import { useEffect, useState } from "react";
import { Plus, ShoppingBag, X, MapPin } from "lucide-react";
import { apiRequest } from "../../api/client";

const EMPTY_PRODUCT = {
  title: "", description: "", price_amount: "", currency: "XOF",
  stock_quantity: "", category: "", country: "", city: "", shipping_scope: "local",
};

export default function Marketplace() {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_PRODUCT);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    search();
  }, []);

  async function search() {
    try {
      const params = query ? `?q=${encodeURIComponent(query)}` : "";
      const data = await apiRequest(`/marketplace/products/search${params}`);
      setProducts(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger les produits.");
    }
  }

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await apiRequest("/marketplace/products", {
        method: "POST",
        body: {
          ...form,
          price_amount: Number(form.price_amount),
          stock_quantity: Number(form.stock_quantity || 0),
        },
      });
      setShowForm(false);
      setForm(EMPTY_PRODUCT);
      search();
    } catch (err) {
      setError(err.detail || "Impossible de publier ce produit.");
    }
  }

  async function handleBuy(product) {
    setFeedback("");
    setError("");
    try {
      await apiRequest("/marketplace/orders", {
        method: "POST",
        body: {
          items: [{ product_id: product.id, quantity: 1 }],
          shipping_country: product.country,
          shipping_city: product.city || "",
          shipping_address: "Adresse à renseigner",
        },
      });
      setFeedback(`Commande passée pour « ${product.title} ».`);
      search();
    } catch (err) {
      setError(err.detail || "Achat impossible.");
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Marketplace</h1>
        <button onClick={() => setShowForm(true)} className="nexus-btn-primary flex items-center gap-2 text-sm">
          <Plus size={16} /> Publier un produit
        </button>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); search(); }} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher un produit..."
          className="nexus-input flex-1"
        />
        <button type="submit" className="nexus-btn-secondary text-sm">Rechercher</button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {feedback && <p className="text-sm text-emerald-400">{feedback}</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {products.map((product) => (
          <div key={product.id} className="nexus-card p-4 flex flex-col">
            <div className="w-full h-28 rounded-xl bg-module-marketplace flex items-center justify-center mb-3">
              <ShoppingBag size={28} className="text-module-marketplace-icon" />
            </div>
            <h3 className="font-medium truncate">{product.title}</h3>
            <p className="text-xs text-nexus-text-muted flex items-center gap-1 mt-0.5">
              <MapPin size={12} /> {product.city ? `${product.city}, ` : ""}{product.country}
            </p>
            <p className="text-sm text-nexus-text-muted mt-2 line-clamp-2 flex-1">{product.description}</p>
            <div className="flex items-center justify-between mt-3">
              <span className="font-semibold">
                {Number(product.price_amount).toLocaleString("fr-FR")} {product.currency}
              </span>
              <button
                onClick={() => handleBuy(product)}
                disabled={product.stock_quantity <= 0}
                className="nexus-btn-primary text-xs py-1.5 px-3"
              >
                {product.stock_quantity > 0 ? "Acheter" : "Épuisé"}
              </button>
            </div>
          </div>
        ))}
        {products.length === 0 && (
          <p className="col-span-full text-center text-nexus-text-muted py-10">
            Aucun produit trouvé. Soyez le premier à publier une annonce.
          </p>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
          <div className="nexus-card w-full max-w-lg p-6 relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setShowForm(false)}
              className="absolute top-4 right-4 text-nexus-text-muted hover:text-nexus-text"
            >
              <X size={20} />
            </button>
            <h2 className="text-lg font-semibold mb-4">Publier un produit</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required placeholder="Titre" value={form.title} onChange={(e) => update("title", e.target.value)} className="nexus-input w-full" />
              <textarea required placeholder="Description" value={form.description} onChange={(e) => update("description", e.target.value)} className="nexus-input w-full" rows={3} />
              <div className="grid grid-cols-2 gap-3">
                <input required type="number" placeholder="Prix" value={form.price_amount} onChange={(e) => update("price_amount", e.target.value)} className="nexus-input w-full" />
                <input placeholder="Devise (XOF)" value={form.currency} onChange={(e) => update("currency", e.target.value)} className="nexus-input w-full" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input required type="number" placeholder="Stock" value={form.stock_quantity} onChange={(e) => update("stock_quantity", e.target.value)} className="nexus-input w-full" />
                <input required placeholder="Catégorie" value={form.category} onChange={(e) => update("category", e.target.value)} className="nexus-input w-full" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input required placeholder="Pays" value={form.country} onChange={(e) => update("country", e.target.value)} className="nexus-input w-full" />
                <input placeholder="Ville" value={form.city} onChange={(e) => update("city", e.target.value)} className="nexus-input w-full" />
              </div>
              <button type="submit" className="nexus-btn-primary w-full">Publier</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
