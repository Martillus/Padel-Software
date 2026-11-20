const TIPS = [
  { icon: "📍", title: "Detrás de la pista, centrado", text: "Por fuera del cristal del fondo, mirando hacia la red." },
  { icon: "⬆️", title: "Lo más alto posible", text: "Con un trípode alto o apoyado en la valla. A la altura de los ojos, los de delante tapan a los de atrás." },
  { icon: "📱", title: "En horizontal y quieto", text: "Sin zoom y sin moverlo durante el partido. 1080p es suficiente." },
  { icon: "👀", title: "Que se vea toda la pista", text: "Las esquinas del fondo lejano, los postes de la red y los pies de los jugadores de tu lado." },
];

export function RecordingTips({ className = "" }: { className?: string }) {
  return (
    <div className={`grid gap-3 sm:grid-cols-2 ${className}`}>
      {TIPS.map((t) => (
        <div key={t.title} className="card flex gap-4 p-4">
          <span className="text-3xl" aria-hidden="true">{t.icon}</span>
          <div>
            <p className="font-bold">{t.title}</p>
            <p className="text-sm text-muted">{t.text}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
