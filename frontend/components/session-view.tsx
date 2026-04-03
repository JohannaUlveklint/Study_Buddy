"use client";

import type { Instruction, Session } from "../types/study-buddy";


type SessionViewProps = {
  instruction: Instruction;
  session: Session;
  disabled: boolean;
  onComplete: () => void;
  onAbort: () => void;
};


export function SessionView({ instruction, session, disabled, onComplete, onAbort }: SessionViewProps) {
  return (
    <section className="panel session-panel">
      <div className="panel-header">
        <p className="eyebrow">Active session</p>
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
          Complete session
        </button>
        <button className="ghost-button" type="button" onClick={onAbort} disabled={disabled}>
          Abort session
        </button>
      </div>
    </section>
  );
}