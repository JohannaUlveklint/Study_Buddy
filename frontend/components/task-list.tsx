"use client";

import type { CSSProperties } from "react";

import { SubjectIcon } from "./subject-icon";
import type { TaskListItem } from "../types/study-buddy";


type TaskListProps = {
  items: TaskListItem[];
  hasRecommendation: boolean;
  disabled: boolean;
  onStart: (taskId: string) => void;
};


export function TaskList({ items, hasRecommendation, disabled, onStart }: TaskListProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <p className="eyebrow">{hasRecommendation ? "Other ways in" : "Tasks"}</p>
        <h2>{hasRecommendation ? "Pick a different task if this one feels easier to start." : "Choose a task and get one step."}</h2>
      </div>

      {items.length === 0 ? (
        <p className="empty-state">No tasks yet. Save one task to unlock the first step.</p>
      ) : (
        <ul className="task-list" aria-label="Task list">
          {items.map((task) => {
            const subjectColor = task.subject?.color ?? "rgba(152, 167, 188, 0.14)";
            const subjectStyle: CSSProperties = {
              borderColor: subjectColor,
              color: task.subject?.color ?? "var(--text-secondary)",
            };

            return (
              <li key={task.id} className="task-card" style={{ borderColor: subjectColor }}>
                <div className="task-card-copy">
                  <div className="task-subject-row">
                    <div className="task-subject-badge" style={subjectStyle}>
                      <SubjectIcon
                        icon={task.subject?.icon}
                        label={task.subject?.name ?? "Unassigned subject"}
                        className="task-subject-icon"
                      />
                      <span>{task.subject?.name ?? "Unassigned"}</span>
                    </div>
                    <p className="task-meta">Created {new Date(task.created_at).toLocaleString()}</p>
                  </div>
                  <p className="task-title">{task.title}</p>
                </div>
                <div className="task-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => onStart(task.id)}
                    disabled={disabled}
                  >
                    {hasRecommendation ? "Start this instead" : "Start this task"}
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}