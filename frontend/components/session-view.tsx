"use client";

import { SubjectIcon } from "./subject-icon";

import type { Instruction, Session, Subject, Task } from "../types/study-buddy";


type SessionViewProps = {
  instruction: Instruction | null;
  session: Session | null;
  disabled: boolean;
  nextTask?: Task | null;
  nextTaskSubject?: Subject | null;
  onStartTask?: (taskId: string) => void;
  onComplete: () => void;
  onAbort: () => void;
};


export function SessionView({
  instruction,
  session,
  disabled,
  nextTask = null,
  nextTaskSubject = null,
  onStartTask,
  onComplete,
  onAbort,
}: SessionViewProps) {
  if (session && instruction) {
    return (
      <section className="panel session-panel session-state">
        <div className="panel-header">
          <p className="eyebrow">Do this now</p>
          <h2>{instruction.title}</h2>
        </div>

        <div className="session-grid">
          <div>
            <p className="stat-label">Difficulty</p>
            <p className="stat-value">Level {instruction.difficulty_level}</p>
          </div>
          <div>
            <p className="stat-label">Planned duration</p>
            <p className="stat-value">{session.planned_duration_minutes ?? 10} minutes</p>
          </div>
        </div>

        <div className="session-actions">
          <button className="primary-button" type="button" onClick={onComplete} disabled={disabled}>
            I finished this step
          </button>
          <button className="ghost-button" type="button" onClick={onAbort} disabled={disabled}>
            Stop for now
          </button>
        </div>
      </section>
    );
  }

  if (nextTask) {
    return (
      <section className="panel session-panel session-state">
        <div className="panel-header">
          <p className="eyebrow">Start here</p>
          <h2>{nextTask.title}</h2>
        </div>

        <p className="session-supporting-copy">This is the narrowest way back in right now.</p>

        <div className="session-subject-row">
          <span
            aria-hidden="true"
            className="session-subject-dot"
            style={{ backgroundColor: nextTaskSubject?.color ?? "#b5bac1" }}
          />
          <SubjectIcon
            icon={nextTaskSubject?.icon}
            label={nextTaskSubject?.name ?? "Suggested task subject"}
            className="task-subject-icon"
          />
          <p className="stat-value">{nextTaskSubject?.name ?? "No subject"}</p>
        </div>

        <div className="session-actions">
          <button
            className="primary-button"
            type="button"
            onClick={() => onStartTask?.(nextTask.id)}
            disabled={disabled}
          >
            Start this step
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="panel session-placeholder session-state">
      <div className="panel-header">
        <p className="eyebrow">Session</p>
        <h2>No step yet.</h2>
      </div>
      <p className="empty-state">Save a task or pick one from the list to get the next action.</p>
    </section>
  );
}