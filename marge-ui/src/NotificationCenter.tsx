import { useEffect, useState, useCallback, useRef } from 'react';

interface Notification {
  notification_id: string;
  title: string;
  message: string;
  created_at: string;
  dismissed: boolean;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const fetchNotifications = useCallback(() => {
    fetch('/api/notifications')
      .then((r) => r.json())
      .then(setNotifications)
      .catch(() => setNotifications([]));
  }, []);

  useEffect(() => {
    fetchNotifications();
    const id = setInterval(fetchNotifications, 3000);
    return () => clearInterval(id);
  }, [fetchNotifications]);

  const dismiss = (notifId: string) => {
    fetch(`/api/notifications/${notifId}/dismiss`, { method: 'POST' })
      .then(() => setTimeout(fetchNotifications, 200));
  };

  const dismissAll = () => {
    fetch('/api/notifications/dismiss_all', { method: 'POST' })
      .then(() => setTimeout(fetchNotifications, 200));
  };

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const count = notifications.length;

  return (
    <div className="notif-center" ref={ref}>
      <button
        className={`notif-bell ${count > 0 ? 'has-notifs' : ''}`}
        onClick={() => setOpen(!open)}
        title={`${count} notification${count !== 1 ? 's' : ''}`}
      >
        {'\u{1F514}'}
        {count > 0 && <span className="notif-badge">{count}</span>}
      </button>

      {open && (
        <div className="notif-dropdown">
          <div className="notif-header">
            <span className="notif-title">Notifications</span>
            {count > 0 && (
              <button className="notif-dismiss-all" onClick={dismissAll}>
                Dismiss All
              </button>
            )}
          </div>
          {count === 0 ? (
            <div className="notif-empty">No notifications</div>
          ) : (
            <div className="notif-list">
              {notifications.map((n) => (
                <div key={n.notification_id} className="notif-item">
                  <div className="notif-item-header">
                    {n.title && <strong className="notif-item-title">{n.title}</strong>}
                    <button
                      className="notif-dismiss"
                      onClick={() => dismiss(n.notification_id)}
                      title="Dismiss"
                    >
                      &times;
                    </button>
                  </div>
                  <div className="notif-item-message">{n.message}</div>
                  <div className="notif-item-time">{formatTime(n.created_at)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
