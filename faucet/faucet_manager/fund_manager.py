import time
import os
import logging
from django.core.cache import cache
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.exceptions import TimeExhausted
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from web3.middleware import geth_poa_middleware
from faucet.faucet_manager.fund_manager_abi import manager_abi
from faucet.models import Chain, BrightUser, LightningConfig
from faucet.helpers import memcache_lock
from faucet.constants import *
from solana.rpc.api import Client
from solana.rpc.core import RPCException
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus
from .anchor_client.accounts.lock_account import LockAccount
from .anchor_client import instructions
from .solana_client import SolanaClient
from .lnpay_client import LNPayClient


class EVMFundManager:
    def __init__(self, chain: Chain):
        self.chain = chain
        self.abi = manager_abi

    class GasPriceTooHigh(Exception):
        pass

    @property
    def w3(self) -> Web3:
        assert self.chain.rpc_url_private is not None
        _w3 = Web3(Web3.HTTPProvider(self.chain.rpc_url_private))
        if self.chain.poa:
            _w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        if _w3.isConnected():
            _w3.eth.set_gas_price_strategy(rpc_gas_price_strategy)
            return _w3
        raise Exception(f"Could not connect to rpc {self.chain.rpc_url_private}")

    @property
    def is_gas_price_too_high(self):
        gas_price = self.w3.eth.gas_price
        if gas_price > self.chain.max_gas_price:
            return True
        return False

    @property
    def account(self) -> LocalAccount:
        return self.w3.eth.account.privateKeyToAccount(self.chain.wallet.main_key)

    def get_checksum_address(self):
        return Web3.toChecksumAddress(self.chain.fund_manager_address.lower())

    @property
    def contract(self):
        return self.w3.eth.contract(address=self.get_checksum_address(), abi=self.abi)

    def transfer(self, bright_user: BrightUser, amount: int):
        tx = self.single_eth_transfer_signed_tx(amount, bright_user.address)
        self.w3.eth.send_raw_transaction(tx.rawTransaction)
        return tx["hash"].hex()

    def multi_transfer(self, data):
        tx = self.multi_eth_transfer_signed_tx(data)
        self.w3.eth.send_raw_transaction(tx.rawTransaction)
        return tx["hash"].hex()

    def single_eth_transfer_signed_tx(self, amount: int, to: str):
        tx_function = self.contract.functions.withdrawEth(amount, to)
        return self.prepare_tx_for_broadcast(tx_function)

    def multi_eth_transfer_signed_tx(self, data):
        tx_function = self.contract.functions.multiWithdrawEth(data)
        return self.prepare_tx_for_broadcast(tx_function)

    def prepare_tx_for_broadcast(self, tx_function):
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_estimation = tx_function.estimateGas({"from": self.account.address})

        if self.is_gas_price_too_high:
            raise self.GasPriceTooHigh()

        tx_data = tx_function.buildTransaction(
            {
                "nonce": nonce,
                "from": self.account.address,
                "gas": gas_estimation,
                "gasPrice": int(self.w3.eth.gas_price * self.chain.gas_multiplier),
            }
        )
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, self.account.key)
        return signed_tx

    def is_tx_verified(self, tx_hash):
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt["status"] == 1:
                return True
            return False
        except TimeExhausted:
            raise


class SolanaFundManager:
    def __init__(self, chain: Chain):
        self.chain = chain
        self.abi = manager_abi

    @property
    def w3(self) -> Client:
        assert self.chain.rpc_url_private is not None
        _w3 = Client(self.chain.rpc_url_private)
        if _w3.is_connected():
            return _w3
        raise Exception(f"Could not connect to rpc {self.chain.rpc_url_private}")

    @property
    def account(self) -> Keypair:
        return Keypair.from_base58_string(self.chain.wallet.main_key)

    @property
    def program_id(self) -> Pubkey:
        return Pubkey.from_string(self.chain.fund_manager_address)

    @property
    def lock_account_seed(self) -> bytes:
        return bytes("locker", "utf-8")

    @property
    def lock_account_address(self) -> Pubkey:
        lock_account_address, nonce = Pubkey.find_program_address(
            [self.lock_account_seed], self.program_id
        )
        return lock_account_address

    @property
    def lock_account(self) -> LocalAccount:
        lock_account_info = self.w3.get_account_info(self.lock_account_address)
        if lock_account_info.value:
            return LockAccount.decode(lock_account_info.value.data)
        return None

    @property
    def is_initialized(self):
        if self.lock_account:
            return self.lock_account.initialized
        return False

    @property
    def owner(self):
        if self.lock_account:
            return self.lock_account.owner
        return None

    @property
    def solana_client(self):
        return SolanaClient(self.w3, self.account)
    
    def is_gas_price_too_high(self, instruction):
        txn = Transaction().add(instruction)
        try:
            fee = self.w3.get_fee_for_message(txn.compile_message()).value
        except RPCException:
            logging.warning("Solana RPCException to get fee for message")
            fee = 0
        if fee > self.chain.max_gas_price:
            return True
        return False

    def multi_transfer(self, data):
        total_withdraw_amount = sum(item["amount"] for item in data)
        if self.is_initialized:
            instruction = instructions.withdraw(
                {"amount": total_withdraw_amount},
                {"lock_account": self.lock_account_address, "owner": self.owner},
            )
            if self.is_gas_price_too_high(instruction):
                raise Exception("GasPriceTooHigh")
            if not self.solana_client.call_program(instruction):
                raise Exception("Could not withdraw assets from solana contract")
            signature = self.solana_client.transfer_many_lamports(
                self.owner,
                [
                    (Pubkey.from_string(item["to"]), int(item["amount"]))
                    for item in data
                ],
            )
            if not signature:
                raise Exception("Transfering lamports to receivers failed")
            return str(signature)
        else:
            raise Exception("The program is not initialized yet")

    def is_tx_verified(self, tx_hash):
        try:
            confirmation_status = (
                self.w3.get_signature_statuses([Signature.from_string(tx_hash)])
                .value[0]
                .confirmation_status
            )
            return confirmation_status in [
                TransactionConfirmationStatus.Confirmed,
                TransactionConfirmationStatus.Finalized,
            ]
        except TimeExhausted:
            raise
        except Exception:
            raise

class LightningFundManager:
    def __init__(self, chain: Chain):
        self.chain = chain

    @property
    def config(self) -> LightningConfig:
        config = LightningConfig.objects.first()
        assert config is not None, "There is no Lightning config"
        return config
    
    @property
    def api_key(self):
        return self.chain.wallet.main_key
    
    @property
    def lnpay_client(self):
        return LNPayClient(
            self.chain.rpc_url_private, 
            self.api_key, 
            self.chain.fund_manager_address
        )
    
    def __check_max_cap_exceeds(self, amount) -> bool:
        try:
            config = self.config
            active_round = (int(time.time() * 1000) / config.period) * config.period
            if active_round != config.current_round:
                config.claimed_amount = 0
                config.current_round = active_round
                config.save()

            return config.claimed_amount + amount > config.period_max_cap
        except Exception as ex:
            logging.error(ex)
            return True

    def multi_transfer(self, data):
        client = self.lnpay_client

        with memcache_lock(MEMCACHE_LIGHTNING_LOCK_KEY, os.getpid()) as acquired:
            assert not acquired, \
                "Could not acquire Lightning multi-transfer lock"
            
            item = data[0]
            assert not self.__check_max_cap_exceeds(item['amount']), \
                "Lightning periodic max cap exceeded"

            pay_result = client.pay_invoice(item["to"])

            if result:
                result = pay_result['lnTx']['id']

                config = self.config
                config.claimed_amount += item['amount']
                config.save()

                cache.delete(MEMCACHE_LIGHTNING_LOCK_KEY)

                return result
            else:
                cache.delete(MEMCACHE_LIGHTNING_LOCK_KEY)
                raise Exception("Lightning: Could not pay the invoice")

    def is_tx_verified(self, tx_hash):
        invoice_status = self.lnpay_client.get_invoice_status(tx_hash)
        return invoice_status['settled'] == 1