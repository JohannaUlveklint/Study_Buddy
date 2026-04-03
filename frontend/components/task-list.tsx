"use client";

import type { Task } from "../types/study-buddy";


type TaskListProps = {
  tasks: Task[];
  disabled: boolean;
  onStart: (taskId: string) => void;
};


export function TaskList({ tasks, disabled, onStart }: TaskListProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <p className="eyebrow">Tasks</p>
        <h2>Queue the next study action.</h2>
      </div>

      {tasks.length === 0 ? (
        <p className="empty-state">No tasks yet. Add one title to create the first study step.</p>
      ) : (
        <ul className="task-list" aria-label="Task list">
          {tasks.map((task) => (
            <li key={task.id} className="task-card">
              <div>
                <p className="task-title">{task.title}</p>
                <p className="task-meta">Created {new Date(task.created_at).toLocaleString()}</p>
              </div>
              <button
                className="secondary-button"
                type="button"
                onClick={() => onStart(task.id)}
                disabled={disabled}
              >
                Start
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}