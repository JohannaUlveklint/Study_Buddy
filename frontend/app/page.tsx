"use client";

import { useEffect, useState } from "react";

import { SessionView } from "../components/session-view";
import { TaskForm } from "../components/task-form";
import { TaskList } from "../components/task-list";
import { abortSession, completeSession, createTask, getNextTask, listSubjects, listTasks, startTask } from "../services/api";
import type { Instruction, Session, Subject, Task, TaskListItem } from "../types/study-buddy";


type PendingAction = "load" | "create" | "start" | "complete" | "abort";


export default function HomePage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [title, setTitle] = useState("");
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [activeInstruction, setActiveInstruction] = useState<Instruction | null>(null);
  const [nextTask, setNextTask] = useState<Task | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadPageData();
  }, []);

  async function loadPageData() {
    setIsPending(true);
    setPendingAction("load");
    try {
      setError(null);
      const [loadedSubjects, loadedTasks, loadedNextTask] = await Promise.all([listSubjects(), listTasks(), getNextTask()]);
      setSubjects(loadedSubjects);
      setTasks(loadedTasks);
      setNextTask(loadedNextTask);
      setSelectedSubjectId((currentSelection) => currentSelection ?? loadedSubjects[0]?.id ?? null);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setIsPending(false);
      setPendingAction(null);
    }
  }

  async function refreshTasksAndNextTask() {
    const [loadedTasks, loadedNextTask] = await Promise.all([listTasks(), getNextTask()]);
    setTasks(loadedTasks);
    setNextTask(loadedNextTask);
  }

  async function handleCreateTask() {
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError("Enter one task before saving it.");
      return;
    }

    if (!selectedSubjectId) {
      setError("Choose a subject before saving the task.");
      return;
    }

    setIsPending(true);
    setPendingAction("create");
    try {
      await createTask(trimmedTitle, selectedSubjectId);
      setTitle("");
      setError(null);
      await refreshTasksAndNextTask();
    } catch (createError) {
      setError(getErrorMessage(createError));
    } finally {
      setIsPending(false);
      setPendingAction(null);
    }
  }

  async function handleStartTask(taskId: string) {
    setIsPending(true);
    setPendingAction("start");
    try {
      const response = await startTask(taskId);
      setActiveSession(response.session);
      setActiveInstruction(response.instruction);
      setNextTask(null);
      setError(null);
    } catch (startError) {
      setError(getErrorMessage(startError));
    } finally {
      setIsPending(false);
      setPendingAction(null);
    }
  }

  async function handleResolveSession(action: "complete" | "abort") {
    if (!activeSession) {
      return;
    }

    setIsPending(true);
    setPendingAction(action);
    try {
      if (action === "complete") {
        await completeSession(activeSession.id);
      } else {
        await abortSession(activeSession.id);
      }

      setActiveSession(null);
      setActiveInstruction(null);
      setError(null);
      await refreshTasksAndNextTask();
    } catch (sessionError) {
      setError(getErrorMessage(sessionError));
    } finally {
      setIsPending(false);
      setPendingAction(null);
    }
  }

  const taskItems: TaskListItem[] = tasks.map((task) => ({
    id: task.id,
    title: task.title,
    created_at: task.created_at,
    subject: subjects.find((subject) => subject.id === task.subject_id) ?? null,
  }));

  const nextTaskSubject = nextTask ? subjects.find((subject) => subject.id === nextTask.subject_id) ?? null : null;
  const showPriorityPanel = activeSession !== null || nextTask !== null;
  const pendingMessage = getPendingMessage(pendingAction);
  const sessionPanel = (
    <div className="column-stack">
      <SessionView
        session={activeSession}
        instruction={activeInstruction}
        nextTask={nextTask}
        nextTaskSubject={nextTaskSubject}
        disabled={isPending}
        onStartTask={(taskId) => void handleStartTask(taskId)}
        onComplete={() => void handleResolveSession("complete")}
        onAbort={() => void handleResolveSession("abort")}
      />
    </div>
  );
  const taskColumn = (
    <div className="column-stack">
      <TaskForm
        title={title}
        subjects={subjects}
        selectedSubjectId={selectedSubjectId}
        disabled={isPending || activeSession !== null}
        onTitleChange={setTitle}
        onSubjectChange={setSelectedSubjectId}
        onSubmit={handleCreateTask}
      />
      <TaskList
        items={taskItems}
        hasRecommendation={nextTask !== null}
        disabled={isPending || activeSession !== null}
        onStart={handleStartTask}
      />
    </div>
  );

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Low-friction study start</p>
        <h1>Start smaller. Begin faster.</h1>
        <p className="hero-copy">
          Pick one task or start the suggested one. Study Buddy keeps the next action narrow.
        </p>
      </section>

      {error ? <p className="status-banner status-error">{error}</p> : null}
      {isPending && pendingMessage ? <p className="status-banner status-working">{pendingMessage}</p> : null}

      <section className="content-grid">
        {showPriorityPanel ? sessionPanel : taskColumn}
        {showPriorityPanel ? taskColumn : sessionPanel}
      </section>
    </main>
  );
}


function getPendingMessage(action: PendingAction | null): string | null {
  switch (action) {
    case "load":
      return "Loading your next step...";
    case "create":
      return "Saving task...";
    case "start":
      return "Preparing the first step...";
    case "complete":
      return "Wrapping up this step...";
    case "abort":
      return "Stopping this step...";
    default:
      return null;
  }
}


function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Something went wrong. Try again.";
}