import logging
import json
import lnpay_py
from lnpay_py.wallet import LNPayWallet
from lnpay_py.lntx import LNPayLnTx
from lnpay_py.utility_helpers import get_request

class LNPayClient:
    def __init__(self, api_url: str, api_key: str, wallet: str) -> None:
        self.api_key = api_key
        self.wallet_address = wallet
        
        lnpay_py.initialize(api_key, params={
            'endpoint_url': api_url
        })

    @property
    def wallet(self):
        return LNPayWallet(self.wallet_address)

    def pay_invoice(self, invoice: str) -> json:
        invoice_params = {
            'payment_request': invoice
        }
        pay_result = self.wallet.pay_invoice(invoice_params)
        if 'lnTx' not in pay_result:
            logging.error(pay_result['message'])
            return False
        return pay_result
    
    @classmethod
    def decode_invoice(cls, invoice: str) -> json:
        return get_request(f"/v1/node/default/payments/decodeinvoice?payment_request={invoice}")
    
    def get_balance(self):
        info = self.wallet.get_info()
        return info['balance']
    
    def get_invoice_status(self, lntx_id):
        ln_tx = LNPayLnTx(lntx_id)
        invoice_result = ln_tx.get_info()
        return invoice_result 