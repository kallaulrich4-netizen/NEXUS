import { useEffect, useState } from "react";
import { Plus, Wallet, TrendingUp, TrendingDown, Download } from "lucide-react";
import { apiRequest, getAccessToken, API_BASE_URL } from "../../api/client";

const EMPTY_TX = { transaction_type: "depense", category: "", amount: "", transaction_date: "" };

export default function Finance() {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [balance, setBalance] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [newAccountName, setNewAccountName] = useState("");
  const [txForm, setTxForm] = useState(EMPTY_TX);
  const [error, setError] = useState("");

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    if (selectedAccountId) {
      loadBalance(selectedAccountId);
      loadTransactions(selectedAccountId);
    }
  }, [selectedAccountId]);

  async function loadAccounts() {
    try {
      const data = await apiRequest("/finance/accounts");
      setAccounts(data);
      if (data.length > 0) setSelectedAccountId(data[0].id);
    } catch (err) {
      setError(err.detail || "Impossible de charger les comptes.");
    }
  }

  async function loadBalance(accountId) {
    try {
      const data = await apiRequest(`/finance/accounts/${accountId}/balance`);
      setBalance(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger le solde.");
    }
  }

  async function loadTransactions(accountId) {
    try {
      const data = await apiRequest(`/finance/transactions?account_id=${accountId}`);
      setTransactions(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger les transactions.");
    }
  }

  async function handleCreateAccount(e) {
    e.preventDefault();
    try {
      await apiRequest("/finance/accounts", { method: "POST", body: { name: newAccountName, currency: "XOF" } });
      setShowAccountForm(false);
      setNewAccountName("");
      loadAccounts();
    } catch (err) {
      setError(err.detail || "Impossible de créer le compte.");
    }
  }

  async function handleCreateTransaction(e) {
    e.preventDefault();
    if (!selectedAccountId) return;
    try {
      await apiRequest("/finance/transactions", {
        method: "POST",
        body: { ...txForm, account_id: selectedAccountId, amount: Number(txForm.amount), currency: "XOF" },
      });
      setTxForm(EMPTY_TX);
      loadBalance(selectedAccountId);
      loadTransactions(selectedAccountId);
    } catch (err) {
      setError(err.detail || "Transaction impossible.");
    }
  }

  async function handleExport(format) {
    const today = new Date();
    const start = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().slice(0, 10);
    const end = today.toISOString().slice(0, 10);
    const token = getAccessToken();
    const url = `${API_BASE_URL}/finance/cashflow/export?start_date=${start}&end_date=${end}&file_format=${format}`;
    const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `tresorerie.${format === "pdf" ? "pdf" : "xlsx"}`;
    link.click();
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Finance</h1>
        <button onClick={() => setShowAccountForm(true)} className="nexus-btn-secondary flex items-center gap-2 text-sm">
          <Plus size={16} /> Nouveau compte
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="flex gap-2 overflow-x-auto pb-1">
        {accounts.map((acc) => (
          <button
            key={acc.id}
            onClick={() => setSelectedAccountId(acc.id)}
            className={`px-4 py-2 rounded-xl text-sm whitespace-nowrap flex items-center gap-2 ${
              selectedAccountId === acc.id ? "bg-nexus-gradient text-white" : "nexus-card"
            }`}
          >
            <Wallet size={14} /> {acc.name}
          </button>
        ))}
      </div>

      {showAccountForm && (
        <form onSubmit={handleCreateAccount} className="nexus-card p-4 flex gap-2">
          <input
            required
            placeholder="Nom du compte"
            value={newAccountName}
            onChange={(e) => setNewAccountName(e.target.value)}
            className="nexus-input flex-1"
          />
          <button type="submit" className="nexus-btn-primary text-sm">Créer</button>
        </form>
      )}

      {balance && (
        <div className="grid grid-cols-3 gap-4">
          <div className="nexus-card p-4">
            <p className="text-xs text-nexus-text-muted">Solde actuel</p>
            <p className="text-xl font-bold mt-1">{Number(balance.current_balance).toLocaleString("fr-FR")}</p>
          </div>
          <div className="nexus-card p-4">
            <p className="text-xs text-nexus-text-muted flex items-center gap-1"><TrendingUp size={12} /> Revenus</p>
            <p className="text-xl font-bold mt-1 text-emerald-400">
              {Number(balance.total_income).toLocaleString("fr-FR")}
            </p>
          </div>
          <div className="nexus-card p-4">
            <p className="text-xs text-nexus-text-muted flex items-center gap-1"><TrendingDown size={12} /> Dépenses</p>
            <p className="text-xl font-bold mt-1 text-red-400">
              {Number(balance.total_expense).toLocaleString("fr-FR")}
            </p>
          </div>
        </div>
      )}

      {selectedAccountId && (
        <>
          <form onSubmit={handleCreateTransaction} className="nexus-card p-4 grid grid-cols-2 md:grid-cols-5 gap-2">
            <select
              value={txForm.transaction_type}
              onChange={(e) => setTxForm((p) => ({ ...p, transaction_type: e.target.value }))}
              className="nexus-input"
            >
              <option value="depense">Dépense</option>
              <option value="revenu">Revenu</option>
            </select>
            <input
              required
              placeholder="Catégorie"
              value={txForm.category}
              onChange={(e) => setTxForm((p) => ({ ...p, category: e.target.value }))}
              className="nexus-input"
            />
            <input
              required
              type="number"
              placeholder="Montant"
              value={txForm.amount}
              onChange={(e) => setTxForm((p) => ({ ...p, amount: e.target.value }))}
              className="nexus-input"
            />
            <input
              required
              type="date"
              value={txForm.transaction_date}
              onChange={(e) => setTxForm((p) => ({ ...p, transaction_date: e.target.value }))}
              className="nexus-input"
            />
            <button type="submit" className="nexus-btn-primary text-sm">Ajouter</button>
          </form>

          <div className="flex items-center justify-between">
            <h2 className="font-medium text-sm text-nexus-text-muted">Transactions récentes</h2>
            <div className="flex gap-2">
              <button onClick={() => handleExport("pdf")} className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5">
                <Download size={13} /> PDF
              </button>
              <button onClick={() => handleExport("excel")} className="nexus-btn-secondary text-xs flex items-center gap-1.5 py-1.5">
                <Download size={13} /> Excel
              </button>
            </div>
          </div>

          <div className="nexus-card divide-y divide-nexus-border">
            {transactions.map((tx) => (
              <div key={tx.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm font-medium capitalize">{tx.category}</p>
                  <p className="text-xs text-nexus-text-muted">{tx.transaction_date}</p>
                </div>
                <span className={tx.transaction_type === "revenu" ? "text-emerald-400" : "text-red-400"}>
                  {tx.transaction_type === "revenu" ? "+" : "-"}{Number(tx.amount).toLocaleString("fr-FR")}
                </span>
              </div>
            ))}
            {transactions.length === 0 && (
              <p className="text-center text-nexus-text-muted py-8 text-sm">Aucune transaction pour ce compte.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
