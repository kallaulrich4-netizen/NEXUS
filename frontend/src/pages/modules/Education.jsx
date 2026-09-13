import { useEffect, useState } from "react";
import { GraduationCap, Lock } from "lucide-react";
import { apiRequest } from "../../api/client";

export default function Education() {
  const [courses, setCourses] = useState([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { loadCourses(); }, []);

  async function loadCourses() {
    try {
      const data = await apiRequest("/education/courses/search");
      setCourses(data);
    } catch (err) {
      setError(err.detail || "Impossible de charger les cours.");
    }
  }

  async function enroll(courseId) {
    setMessage("");
    setError("");
    try {
      await apiRequest(`/education/courses/${courseId}/enroll`, { method: "POST" });
      setMessage("Inscription réussie ! Retrouvez ce cours dans vos inscriptions.");
    } catch (err) {
      if (err.status === 402) {
        setError("Ce cours est réservé aux comptes premium.");
      } else if (err.status === 409) {
        setMessage("Vous êtes déjà inscrit à ce cours.");
      } else {
        setError(err.detail || "Inscription impossible.");
      }
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-xl font-semibold flex items-center gap-2"><GraduationCap size={22} /> Éducation</h1>

      {error && <p className="text-sm text-red-400">{error}</p>}
      {message && <p className="text-sm text-emerald-400">{message}</p>}

      <div className="grid md:grid-cols-2 gap-4">
        {courses.map((course) => (
          <article key={course.id} className="nexus-card p-4 flex flex-col">
            <div className="flex items-start justify-between">
              <h3 className="font-medium">{course.title}</h3>
              {course.is_premium && <Lock size={14} className="text-amber-400 shrink-0 mt-1" />}
            </div>
            <p className="text-xs text-nexus-text-muted capitalize mt-1">
              {course.discipline.replace(/_/g, " ")} • {course.level}
            </p>
            <button onClick={() => enroll(course.id)} className="nexus-btn-secondary text-sm mt-3">
              S'inscrire
            </button>
          </article>
        ))}
        {courses.length === 0 && (
          <p className="col-span-full text-center text-nexus-text-muted py-12">Aucun cours publié pour l'instant.</p>
        )}
      </div>
    </div>
  );
}
