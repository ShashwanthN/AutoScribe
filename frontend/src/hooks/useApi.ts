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
    enabled: Boolean(projectId) && (phase === "ideation" || phase === "structure")
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
