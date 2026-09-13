import { useEffect, useState } from "react";
import { Heart, MessageCircle, Send } from "lucide-react";
import { apiRequest } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

export default function Social() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [content, setContent] = useState("");
  const [isPosting, setIsPosting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadFeed();
  }, []);

  async function loadFeed() {
    try {
      const data = await apiRequest("/social/feed");
      setPosts(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger le fil d'actualité.");
    }
  }

  async function handlePost(e) {
    e.preventDefault();
    if (!content.trim() || isPosting) return;
    setIsPosting(true);
    try {
      await apiRequest("/social/posts", { method: "POST", body: { content } });
      setContent("");
      loadFeed();
    } catch (err) {
      setError(err.detail || "Publication impossible.");
    } finally {
      setIsPosting(false);
    }
  }

  async function toggleLike(postId) {
    try {
      await apiRequest(`/social/posts/${postId}/like`, { method: "POST" });
      loadFeed();
    } catch {
      // Silencieux : un like manqué n'est pas bloquant pour l'utilisateur.
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold">Réseau Social</h1>

      <form onSubmit={handlePost} className="nexus-card p-4 space-y-3">
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-full bg-nexus-gradient flex items-center justify-center text-sm font-semibold text-white shrink-0">
            {user?.full_name?.[0]?.toUpperCase() || "?"}
          </div>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Quoi de neuf ?"
            rows={3}
            className="nexus-input w-full resize-none"
          />
        </div>
        <div className="flex justify-end">
          <button type="submit" disabled={isPosting} className="nexus-btn-primary flex items-center gap-2 text-sm">
            <Send size={15} /> Publier
          </button>
        </div>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="space-y-4">
        {posts.map((post) => (
          <article key={post.id} className="nexus-card p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-full bg-nexus-surface-hover" />
              <div className="text-sm text-nexus-text-muted">
                {new Date(post.created_at).toLocaleString("fr-FR")}
              </div>
            </div>
            <p className="text-sm whitespace-pre-wrap">{post.content}</p>
            <div className="flex items-center gap-5 mt-3 text-sm text-nexus-text-muted">
              <button
                onClick={() => toggleLike(post.id)}
                className={`flex items-center gap-1.5 hover:text-nexus-purple ${
                  post.liked_by_current_user ? "text-nexus-purple" : ""
                }`}
              >
                <Heart size={16} fill={post.liked_by_current_user ? "currentColor" : "none"} />
                {post.likes_count}
              </button>
              <span className="flex items-center gap-1.5">
                <MessageCircle size={16} /> {post.comments_count}
              </span>
            </div>
          </article>
        ))}
        {posts.length === 0 && (
          <p className="text-center text-nexus-text-muted py-10">
            Votre fil est vide pour l'instant — abonnez-vous à d'autres utilisateurs ou publiez votre premier post.
          </p>
        )}
      </div>
    </div>
  );
}
