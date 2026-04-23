"""
MUSU Payment Gateway client.

In development, USE_MUSU_MOCK=True returns a fake confirmation immediately.
In production, this talks to the real MUSU API and handles webhook callbacks.

MUSU API contract (based on Gambia mobile money gateway pattern):
  POST /initiate  → returns { reference, status, payment_url }
  POST /verify    → returns { status, transaction_id, amount_paid }
  Webhook         → POST to our /payments/callback/ with HMAC-SHA256 signature
"""
import hashlib
import hmac
import logging
import uuid
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MUSUClient:
    def __init__(self):
        self.base_url    = settings.MUSU_API_BASE_URL
        self.merchant_id = settings.MUSU_MERCHANT_ID
        self.api_key     = settings.MUSU_API_KEY
        self.mock        = getattr(settings, 'USE_MUSU_MOCK', True)

    def _headers(self):
        return {
            'X-Merchant-ID': self.merchant_id,
            'X-API-Key':     self.api_key,
            'Content-Type':  'application/json',
        }

    def initiate_payment(self, case_id: str, amount: Decimal, payer_phone: str,
                         callback_url: str, description: str) -> dict:
        """
        Initiate a payment request with MUSU.
        Returns: { reference, payment_url, status }
        """
        if self.mock:
            return self._mock_initiate(case_id, amount)

        payload = {
            'merchant_id':  self.merchant_id,
            'reference':    f'GJ-{case_id[:8].upper()}',
            'amount':       str(amount),
            'currency':     'GMD',
            'payer_phone':  payer_phone,
            'callback_url': callback_url,
            'description':  description,
        }
        try:
            resp = requests.post(
                f'{self.base_url}/initiate',
                json=payload, headers=self._headers(), timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error('MUSU initiate_payment failed: %s', e)
            raise

    def verify_payment(self, reference: str) -> dict:
        """
        Verify payment status by reference.
        Returns: { status, transaction_id, amount_paid }
        """
        if self.mock:
            return self._mock_verify(reference)

        try:
            resp = requests.get(
                f'{self.base_url}/verify/{reference}',
                headers=self._headers(), timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error('MUSU verify_payment failed: %s', e)
            raise

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        MUSU signs webhook callbacks with HMAC-SHA256.
        Header: X-MUSU-Signature: sha256=<hex_digest>
        """
        secret = settings.MUSU_WEBHOOK_SECRET.encode()
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        # Compare received signature (strip 'sha256=' prefix if present)
        received = signature.replace('sha256=', '')
        return hmac.compare_digest(expected, received)

    # ── Mock implementations ───────────────────────────────────────────────

    def _mock_initiate(self, case_id: str, amount: Decimal) -> dict:
        """In dev: instantly returns a fake reference."""
        reference = f'MOCK-{uuid.uuid4().hex[:12].upper()}'
        logger.info('[MUSU MOCK] Initiated payment — reference: %s, amount: GMD %s', reference, amount)
        return {
            'reference':   reference,
            'payment_url': f'http://localhost:5173/mock-payment/{reference}',
            'status':      'initiated',
        }

    def _mock_verify(self, reference: str) -> dict:
        """In dev: always returns confirmed."""
        logger.info('[MUSU MOCK] Verified payment — reference: %s → confirmed', reference)
        return {
            'status':         'confirmed',
            'transaction_id': f'TXN-{uuid.uuid4().hex[:10].upper()}',
            'amount_paid':    None,  # will be filled from our stored amount_due
        }


musu_client = MUSUClient()
