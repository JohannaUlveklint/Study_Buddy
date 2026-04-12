"use client";

import type { Subject } from "../types/study-buddy";

type TaskFormProps = {
  title: string;
  subjects: Subject[];
  selectedSubjectId: string | null;
  disabled: boolean;
  onTitleChange: (value: string) => void;
  onSubjectChange: (value: string) => void;
  onSubmit: () => void;
};


export function TaskForm({
  title,
  subjects,
  selectedSubjectId,
  disabled,
  onTitleChange,
  onSubjectChange,
  onSubmit,
}: TaskFormProps) {
  const isSubmitDisabled = disabled || !title.trim() || subjects.length === 0 || !selectedSubjectId;

  return (
    <section className="panel panel-accent">
      <div className="panel-header">
        <p className="eyebrow">Add one task</p>
        <h2>Name the thing you can start now.</h2>
        <p className="panel-helper">Keep it concrete. You only need enough detail to begin.</p>
      </div>

      <form
        className="task-form-stack"
        onSubmit={(event) => {
          event.preventDefault();

          if (!isSubmitDisabled) {
            onSubmit();
          }
        }}
      >
        <div>
          <label className="field-label" htmlFor="task-title">
            Task
          </label>
          <div className="task-form-row">
            <input
              id="task-title"
              className="text-input"
              type="text"
              value={title}
              onChange={(event) => onTitleChange(event.target.value)}
              placeholder="Read two pages of chapter 2"
              disabled={disabled}
            />
          </div>
        </div>

        <div>
          <label className="field-label" htmlFor="task-subject">
            Subject
          </label>
          <select
            id="task-subject"
            className="select-input"
            value={selectedSubjectId ?? ""}
            onChange={(event) => onSubjectChange(event.target.value)}
            disabled={disabled || subjects.length === 0}
          >
            {subjects.length === 0 ? <option value="">No subjects available</option> : null}
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>
        </div>

        <button className="primary-button" type="submit" disabled={isSubmitDisabled}>
          Save task
        </button>
      </form>
    </section>
  );
}