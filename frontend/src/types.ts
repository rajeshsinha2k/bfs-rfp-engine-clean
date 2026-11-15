export interface HITLActionButton {
  action_id: string;
  label: string;
  variant: 'primary' | 'danger' | 'secondary' | string;
}

export interface ChatMessageEvent {
  rfp_id?: string;
  sender: string;
  phase: number;
  message_english: string;
  message_native?: string;
  artifact_type?: string;
  artifact_payload?: Record<string, any>;
  hitl_buttons: HITLActionButton[];
}

export interface RFPProjectSummary {
  rfp_id: string;
  client_name_redacted: string;
  detected_language: string;
  current_phase: number;
  workflow_status: string;
  updated_at: string;
}
