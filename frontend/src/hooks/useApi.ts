import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { ContentType, Phase, PhaseFile } from "../types";

export function useProjects() {
  return useQuery({ queryKey: ["projects"], queryFn: api.listProjects });
}

export function useProject(projectId: string | null) {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId as string),
    enabled: Boolean(projectId)
  });
}

export function useVoices() {
  return useQuery({ queryKey: ["voices"], queryFn: api.listVoices });
}

export function useFile(projectId: string | null, name: PhaseFile) {
  return useQuery({
    queryKey: ["file", projectId, name],
    queryFn: () => api.getFile(projectId as string, name),
    enabled: Boolean(projectId)
  });
}

export function useTranscript(projectId: string | null, phase: Phase) {
  return useQuery({
    queryKey: ["transcript", projectId, phase],
    queryFn: () => api.getTranscript(projectId as string, phase),
    enabled: Boolean(projectId) && (phase === "ideation" || phase === "structure" || phase === "drafting")
  });
}

export function useActivity(projectId: string | null) {
  return useQuery({
    queryKey: ["activity", projectId],
    queryFn: () => api.getActivity(projectId as string),
    enabled: Boolean(projectId)
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createProject,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] })
  });
}

export function usePatchProject(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<{ title: string; content_type: ContentType; voice_id: string | null }>) =>
      api.patchProject(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    }
  });
}

export function useAdvancePhase(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.advanceProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    }
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: string) => api.deleteProject(projectId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] })
  });
}

export function useSaveFile(projectId: string, name: PhaseFile) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => api.saveFile(projectId, name, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["file", projectId, name] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    }
  });
}

export function useVoiceTemplates() {
  return useQuery({ queryKey: ["voice-templates"], queryFn: api.listVoiceTemplates });
}

export function usePersons() {
  return useQuery({ queryKey: ["persons"], queryFn: api.listPersons });
}

export function usePerson(personId: string | null) {
  return useQuery({
    queryKey: ["person", personId],
    queryFn: () => api.getPerson(personId as string),
    enabled: Boolean(personId)
  });
}

export function useCreatePerson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.createPerson(name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["persons"] })
  });
}

export function useRenamePerson(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.renamePerson(personId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["person", personId] });
      queryClient.invalidateQueries({ queryKey: ["persons"] });
    }
  });
}

export function useDeletePerson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (personId: string) => api.deletePerson(personId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["persons"] })
  });
}

export function useArticles(personId: string | null) {
  return useQuery({
    queryKey: ["articles", personId],
    queryFn: () => api.listArticles(personId as string),
    enabled: Boolean(personId)
  });
}

export function useAddArticle(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string; text: string }) => api.addArticle(personId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles", personId] });
      queryClient.invalidateQueries({ queryKey: ["person", personId] });
      queryClient.invalidateQueries({ queryKey: ["persons"] });
    }
  });
}

export function useUpdateArticle(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ articleId, ...payload }: { articleId: string; title: string; text: string }) =>
      api.updateArticle(personId, articleId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["articles", personId] })
  });
}

export function useDeleteArticle(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (articleId: string) => api.deleteArticle(personId, articleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["articles", personId] });
      queryClient.invalidateQueries({ queryKey: ["person", personId] });
      queryClient.invalidateQueries({ queryKey: ["persons"] });
    }
  });
}

export function useRuns(personId: string | null) {
  return useQuery({
    queryKey: ["runs", personId],
    queryFn: () => api.listRuns(personId as string),
    enabled: Boolean(personId)
  });
}

export function useRun(personId: string | null, runId: string | null) {
  return useQuery({
    queryKey: ["run", personId, runId],
    queryFn: () => api.getRun(personId as string, runId as string),
    enabled: Boolean(personId) && Boolean(runId)
  });
}

export function useActivateRun(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.activateRun(personId, runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["person", personId] });
      queryClient.invalidateQueries({ queryKey: ["persons"] });
      queryClient.invalidateQueries({ queryKey: ["voices"] });
    }
  });
}

export function useDeleteRun(personId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => api.deleteRun(personId, runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs", personId] });
      queryClient.invalidateQueries({ queryKey: ["person", personId] });
      queryClient.invalidateQueries({ queryKey: ["persons"] });
      queryClient.invalidateQueries({ queryKey: ["voices"] });
    }
  });
}
