export type Subject = {
  id: string;
  name: string;
  color: string;
  icon: string;
};

export type Task = {
  id: string;
  title: string;
  subject_id: string | null;
  created_at: string;
  is_completed: boolean;
};

export type TaskListItem = {
  id: string;
  title: string;
  created_at: string;
  subject: Subject | null;
};

export type Session = {
  id: string;
  task_id: string | null;
  subtask_id: string | null;
  started_at: string;
  ended_at: string | null;
  planned_duration_minutes: number | null;
  actual_duration_minutes: number | null;
  was_completed: boolean;
  was_aborted: boolean;
};

export type Instruction = {
  title: string;
  difficulty_level: number;
};

export type TaskStartResponse = {
  session: Session;
  instruction: Instruction;
};