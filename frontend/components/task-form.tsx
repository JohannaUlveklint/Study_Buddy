"use client";

type TaskFormProps = {
  title: string;
  disabled: boolean;
  onTitleChange: (value: string) => void;
  onSubmit: () => void;
};


export function TaskForm({ title, disabled, onTitleChange, onSubmit }: TaskFormProps) {
  return (
    <section className="panel panel-accent">
      <div className="panel-header">
        <p className="eyebrow">Create</p>
        <h2>Start with one small task.</h2>
      </div>

      <label className="field-label" htmlFor="task-title">
        Task title
      </label>
      <div className="task-form-row">
        <input
          id="task-title"
          className="text-input"
          type="text"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          placeholder="Read chapter 2"
          disabled={disabled}
        />
        <button className="primary-button" type="button" onClick={onSubmit} disabled={disabled}>
          Add task
        </button>
      </div>
    </section>
  );
}