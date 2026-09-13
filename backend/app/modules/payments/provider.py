"""
Abstraction des fournisseurs de paiement.

Même principe que `ai_assistant/provider.py` et `studio/ai_video_provider.py` :
le reste de l'application ne parle jamais directement à MTN, Orange ou
un processeur de cartes bancaires. Elle appelle `PaymentProvider.charge`,
qui encapsule la logique propre à chaque fournisseur.

En production :
- MTN Mobile Money : intégration via l'API MTN MoMo (déclenche une
  demande de paiement sur le téléphone du client, confirmée par code USSD).
- Orange Money : intégration via l'API Orange Money Web Payment.
- Visa/Mastercard : intégration via un processeur de paiement carte
  conforme PCI-DSS (ex: Stripe, Flutterwave, CinetPay selon votre marché) —
  ne stockez JAMAIS de numéro de carte vous-même, laissez le processeur
  s'en charger et ne conservez que sa référence de transaction.

Aucun de ces services n'étant accessible depuis cet environnement de
développement (pas d'accès réseau, pas de clés d'API réelles), chaque
implémentation par défaut place honnêtement le paiement en attente.
"""
from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    @abstractmethod
    def charge(self, amount: float, currency: str, method: str, user_reference: str) -> dict:
        """
        Déclenche une tentative de paiement. Retourne un dict avec au
        moins {"status": ..., "provider_reference": ... | None,
        "failure_reason": ... | None}.
        """
        raise NotImplementedError


class PendingPaymentProvider(PaymentProvider):
    """
    Provider par défaut : place tout paiement en attente. Ne prétend
    JAMAIS qu'un paiement a réussi s'il n'a pas réellement été traité
    par un fournisseur réel.
    """

    def charge(self, amount: float, currency: str, method: str, user_reference: str) -> dict:
        return {
            "status": "en_attente",
            "provider_reference": None,
            "failure_reason": (
                f"Aucun fournisseur réel branché pour la méthode « {method} ». "
                "Branchez l'API MTN MoMo, Orange Money, ou un processeur carte "
                "conforme PCI-DSS dans ce fichier avant la mise en production."
            ),
        }


def get_payment_provider(method: str) -> PaymentProvider:
    """
    Point d'injection unique. En production, retournez ici l'implémentation
    réelle correspondant à `method` (ex: MtnMomoProvider() pour
    "mtn_mobile_money", OrangeMoneyProvider() pour "orange_money",
    StripeCardProvider() pour "visa"/"mastercard").
    """
    return PendingPaymentProvider()
