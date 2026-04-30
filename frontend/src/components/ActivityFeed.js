// frontend/src/components/ActivityFeed.js
import React, { useState, useEffect } from 'react';
import './ActivityFeed.css';

// Using mock data since backend doesn't store a feed
const mockActivities = [
  { id: 1, type: 'Image', mode: 'LOCAL', time: 'Just now' },
  { id: 2, type: 'Video', mode: 'SPLIT', time: '2m ago' },
  { id: 3, type: 'Image', mode: 'CLOUD', time: '5m ago' },
];

const ActivityFeed = ({ newTask }) => {
  const [activities, setActivities] = useState(mockActivities);

  useEffect(() => {
    if (newTask && newTask.result) {
      setActivities(prev => {
        const newAct = {
          id: Date.now(),
          type: newTask.file_type === 'video' ? 'Video' : 'Image',
          mode: newTask.result.mode_used || newTask.mode || 'LOCAL',
          time: 'Just now'
        };
        return [newAct, ...prev].slice(0, 4);
      });
    }
  }, [newTask]);

  if (!activities || activities.length === 0) return null;

  return (
    <div className="glass-card activity-feed fade-in" style={{ animationDelay: '0.4s' }}>
      <div className="section-title">
        <span className="icon">📋</span> Recent Activity
      </div>
      <div className="activity-list">
        {activities.map((act) => (
          <div key={act.id} className="activity-item">
            <span className="activity-icon">✔</span>
            <span className="activity-text">
              {act.type} processed (<strong className={`text-${act.mode.toLowerCase()}`}>{act.mode}</strong>)
            </span>
            <span className="activity-time">{act.time}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ActivityFeed;
