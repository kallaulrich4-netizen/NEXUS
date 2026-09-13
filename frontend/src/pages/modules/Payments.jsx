import { useEffect, useState } from "react";
import { CreditCard, Check, Crown, History, XCircle, Loader2 } from "lucide-react";
import { apiRequest } from "../../api/client";

const METHOD_LABELS = {
  mtn_mobile_money: "MTN Mobile Money",
  orange_money: "Orange Money",
  visa: "Visa",
  mastercard: "Mastercard",
  autre: "Autre",
};

const STATUS_LABELS = {
  reussi: { label: "Réussi", className: "text-emerald-400" },
  echoue: { label: "Échoué", className: "text-red-400" },
  en_attente: { label: "En attente", className: "text-amber-400" },
  rembourse: { label: "Remboursé", className: "text-nexus-text-muted" },
};

export default function Payments() {
  const [plans, setPlans] = useState([]);
  const [activeSubscription, setActiveSubscription] = useState(null);
  const [payments, setPayments] = useState([]);
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [paymentMethod, setPaymentMethod] = useState("mtn_mobile_money");
  const [isSubscribing, setIsSubscribing] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setIsLoading(true);
    try {
      const [plansData, activeData, paymentsData] = await Promise.all([
        apiRequest("/payments/plans"),
        apiRequest("/payments/subscriptions/mine/active"),
        apiRequest("/payments/payments/mine"),
      ]);
      setPlans(plansData);
      setActiveSubscription(activeData);
      setPayments(paymentsData);
      if (plansData.length > 0) setSelectedPlanId(plansData[0].id);
    } catch (err) {
      setError(err.detail || "Impossible de charger les informations de paiement.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubscribe(e) {
    e.preventDefault();
    if (!selectedPlanId) return;
    setIsSubscribing(true);
    setError("");
    setLastResult(null);
    try {
      const result = await apiRequest("/payments/subscribe", {
        method: "POST",
        body: { plan_id: selectedPlanId, payment_method: paymentMethod },
      });
      setLastResult(result);
      await loadAll();
    } catch (err) {
      setError(err.detail || "Le paiement n'a pas pu être initié.");
    } finally {
      setIsSubscribing(false);
    }
  }

  async function handleCancel(subscriptionId) {
    try {
      await apiRequest(`/payments/subscriptions/${subscriptionId}/cancel`, { method: "POST" });
      await loadAll();
    } catch (err) {
      setError(err.detail || "Impossible d'annuler l'abonnement.");
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto flex items-center justify-center py-24 text-nexus-text-muted">
        <Loader2 className="animate-spin mr-2" size={18} /> Chargement...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <CreditCard size={20} /> Paiement
        </h1>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {/* Statut de l'abonnement */}
      <div className="nexus-card p-5">
        <div className="flex items-center gap-2 mb-1">
          <Crown size={18} className="text-amber-400" />
          <h2 className="font-medium">Statut de l'abonnement</h2>
        </div>
        {activeSubscription ? (
          <div className="mt-3 flex items-center justify-between flex-wrap gap-3">
            <div>
              <p className="text-sm">
                Abonnement <span className="font-semibold text-emerald-400">actif</span>
              </p>
              <p className="text-xs text-nexus-text-muted mt-1">
                Valable jusqu'au{" "}
                {activeSubscription.ends_at
                  ? new Date(activeSubscription.ends_at).toLocaleDateString("fr-FR")
                  : "—"}
              </p>
            </div>
            <button
              onClick={() => handleCancel(activeSubscription.id)}
              className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5"
            >
              <XCircle size={14} /> Annuler l'abonnement
            </button>
          </div>
        ) : (
          <p className="text-sm text-nexus-text-muted mt-2">
            Vous n'avez aucun abonnement actif pour le moment. Choisissez un plan ci-dessous pour débloquer les
            fonctionnalités premium de Nexus.
          </p>
        )}
      </div>

      {/* Plans disponibles */}
      <div>
        <h2 className="font-medium text-sm text-nexus-text-muted mb-3">Plans disponibles</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((plan) => (
            <button
              key={plan.id}
              onClick={() => setSelectedPlanId(plan.id)}
              className={`nexus-card p-5 text-left transition-colors ${
                selectedPlanId === plan.id ? "ring-2 ring-nexus-blue" : "hover:bg-nexus-surface-hover"
              }`}
            >
              <p className="font-semibold">{plan.name}</p>
              <p className="text-2xl font-bold mt-2">
                {Number(plan.price_amount).toLocaleString("fr-FR")}{" "}
                <span className="text-sm font-normal text-nexus-text-muted">{plan.currency}</span>
              </p>
              <p className="text-xs text-nexus-text-muted mt-1">
                Valable {plan.duration_days} jour{plan.duration_days > 1 ? "s" : ""}
              </p>
              {selectedPlanId === plan.id && (
                <p className="text-xs text-nexus-blue flex items-center gap-1 mt-3">
                  <Check size={12} /> Sélectionné
                </p>
              )}
            </button>
          ))}
          {plans.length === 0 && (
            <p className="text-sm text-nexus-text-muted col-span-3">Aucun plan disponible pour le moment.</p>
          )}
        </div>
      </div>

      {/* Formulaire d'abonnement */}
      {plans.length > 0 && (
        <form onSubmit={handleSubscribe} className="nexus-card p-4 flex flex-wrap gap-2 items-center">
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className="nexus-input flex-1 min-w-[180px]"
          >
            {Object.entries(METHOD_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <button type="submit" disabled={isSubscribing} className="nexus-btn-primary text-sm flex items-center gap-2">
            {isSubscribing && <Loader2 size={14} className="animate-spin" />}
            S'abonner
          </button>
        </form>
      )}

      {lastResult && (
        <div className="nexus-card p-4 text-sm">
          <p>
            Tentative de paiement :{" "}
            <span className={STATUS_LABELS[lastResult.payment.status]?.className || ""}>
              {STATUS_LABELS[lastResult.payment.status]?.label || lastResult.payment.status}
            </span>
          </p>
          {lastResult.payment.failure_reason && (
            <p className="text-xs text-nexus-text-muted mt-1">{lastResult.payment.failure_reason}</p>
          )}
        </div>
      )}

      {/* Historique des paiements */}
      <div>
        <h2 className="font-medium text-sm text-nexus-text-muted mb-3 flex items-center gap-2">
          <History size={14} /> Historique des paiements
        </h2>
        <div className="nexus-card divide-y divide-nexus-border">
          {payments.map((payment) => (
            <div key={payment.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="text-sm font-medium">{METHOD_LABELS[payment.method] || payment.method}</p>
                <p className="text-xs text-nexus-text-muted">
                  {new Date(payment.created_at).toLocaleDateString("fr-FR")}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold">
                  {Number(payment.amount).toLocaleString("fr-FR")} {payment.currency}
                </p>
                <p className={`text-xs ${STATUS_LABELS[payment.status]?.className || "text-nexus-text-muted"}`}>
                  {STATUS_LABELS[payment.status]?.label || payment.status}
                </p>
              </div>
            </div>
          ))}
          {payments.length === 0 && (
            <p className="text-center text-nexus-text-muted py-8 text-sm">Aucun paiement pour le moment.</p>
          )}
        </div>
      </div>
    </div>
  );
}
