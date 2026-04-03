"use client";

import { useEffect, useState } from "react";

import { SessionView } from "../components/session-view";
import { TaskForm } from "../components/task-form";
import { TaskList } from "../components/task-list";
import { abortSession, completeSession, createTask, listTasks, startTask } from "../services/api";
import type { Instruction, Session, Task } from "../types/study-buddy";


export default function HomePage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [activeInstruction, setActiveInstruction] = useState<Instruction | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadTasks();
  }, []);

  async function loadTasks() {
    try {
      setError(null);
      setTasks(await listTasks());
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    }
  }

  async function handleCreateTask() {
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError("Enter a task title before creating a task.");
      return;
    }

    setIsPending(true);
    try {
      await createTask(trimmedTitle);
      setTitle("");
      setError(null);
      await loadTasks();
    } catch (createError) {
      setError(getErrorMessage(createError));
    } finally {
      setIsPending(false);
    }
  }

  async function handleStartTask(taskId: string) {
    setIsPending(true);
    try {
      const response = await startTask(taskId);
      setActiveSession(response.session);
      setActiveInstruction(response.instruction);
      setError(null);
    } catch (startError) {
      setError(getErrorMessage(startError));
    } finally {
      setIsPending(false);
    }
  }

  async function handleResolveSession(action: "complete" | "abort") {
    if (!activeSession) {
      return;
    }

    setIsPending(true);
    try {
      if (action === "complete") {
        await completeSession(activeSession.id);
      } else {
        await abortSession(activeSession.id);
      }

      setActiveSession(null);
      setActiveInstruction(null);
      setError(null);
      await loadTasks();
    } catch (sessionError) {
      setError(getErrorMessage(sessionError));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Study Buddy</p>
        <h1>Turn one task into one study action.</h1>
        <p className="hero-copy">
          Create a task, start it, get a single instruction, and finish the session without leaving the page.
        </p>
      </section>

      {error ? <p className="status-banner status-error">{error}</p> : null}
      {isPending ? <p className="status-banner status-working">Working...</p> : null}

      <section className="content-grid">
        <div className="column-stack">
          <TaskForm
            title={title}
            disabled={isPending || activeSession !== null}
            onTitleChange={setTitle}
            onSubmit={handleCreateTask}
          />
          <TaskList tasks={tasks} disabled={isPending || activeSession !== null} onStart={handleStartTask} />
        </div>

        <div className="column-stack">
          {activeSession && activeInstruction ? (
            <SessionView
              session={activeSession}
              instruction={activeInstruction}
              disabled={isPending}
              onComplete={() => void handleResolveSession("complete")}
              onAbort={() => void handleResolveSession("abort")}
            />
          ) : (
            <section className="panel session-placeholder">
              <div className="panel-header">
                <p className="eyebrow">Session</p>
                <h2>No active session.</h2>
              </div>
              <p className="empty-state">Start a task to reveal the single instruction for this phase.</p>
            </section>
          )}
        </div>
      </section>
    </main>
  );
}


function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Unexpected error.";
}