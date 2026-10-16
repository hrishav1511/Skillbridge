export enum LoadingState {
  IDLE = 'IDLE',
  LOADING = 'LOADING',
  SUCCESS = 'SUCCESS',
  ERROR = 'ERROR'
}

export type FavoriteType = 'Tutor' | 'Service';

export interface FavoriteItem {
  id: string;
  type: FavoriteType;
  title: string;
  subtitle: string;
  imageUrl?: string | null;
  metadata?: string;
  item: unknown;
}

/**
 * The notification types the API actually emits.
 *
 * This list previously named two types the backend never sends
 * ('SERVICE_APPROVED', 'SERVICE_REVISION_APPROVED'), so nothing could match on
 * it. Keep it in step with the `notification_type` values in the backend.
 */
export type NotificationType =
  | 'CHAT_MESSAGE_RECEIVED'
  | 'RESCHEDULE_PROPOSED'
  | 'REVIEW_REMOVED'
  | 'REVIEW_REPORTED'
  | 'REVIEW_REPORT_DISMISSED'
  | 'SERVICE_DISABLED_AFTER_REPORT'
  | 'SERVICE_REPORTED'
  | 'SERVICE_REVIEW_CREATED'
  | 'SERVICE_UPDATED'
  | 'SESSION_ACCEPTED'
  | 'SESSION_CANCELLED'
  | 'SESSION_DECLINED'
  | 'SESSION_REQUESTED'
  | 'TUTOR_DISABLED_AFTER_REPORT'
  | 'TUTOR_PROFILE_APPROVED'
  | 'TUTOR_PROFILE_REJECTED'
  | 'TUTOR_REPORTED'
  | 'TUTOR_REVIEW_CREATED';

/**
 * Entity references carried on a notification.
 *
 * Which keys are present depends on the type; they are the references the
 * notification list uses to route to the thing the notification is about.
 */
export interface NotificationData {
  booking_id?: string | null;
  chat_room_id?: string | null;
  message_id?: string | null;
  proposal_id?: string | null;
  report_id?: string | null;
  revision_id?: string | null;
  revision_type?: 'CREATE' | 'UPDATE' | 'DELETE';
  review_id?: string | null;
  sender_id?: string | null;
  service_id?: string | null;
  tutor_id?: string | null;
}

/** @deprecated Kept as an alias while call sites migrate to NotificationData. */
export type ServiceApprovalData = NotificationData;

export interface Notification {
  id: string;
  user_id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  data: NotificationData | null;
  is_read: boolean;
  is_delivered?: boolean;
  created_at: string | null;
}

export interface NotificationListResponse {
  success: boolean;
  message: string;
  metadata: {
    total: number;
    unread_count: number;
    limit: number;
    offset: number;
  };
  data: Notification[];
}

export interface NotificationWebSocketFrame {
  event: 'notification';
  payload: Notification;
}

export interface ChatMember {
  user_id: string;
  full_name: string;
  email: string;
}

export interface ChatLastMessage {
  id: string;
  sender_id: string;
  content: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  chat_room_id: string;
  sender_id: string;
  content: string;
  created_at: string;
}

export interface ChatRoom {
  chat_room_id: string;
  name: string | null;
  room_type: 'DIRECT' | 'GROUP' | string;
  members: ChatMember[];
  last_message: ChatLastMessage | null;
}

export interface UserSummary {
  full_name: string;
  email: string;
  phone: string;
  password?: string;
  status: string;
  has_registered: boolean;
  is_verified: boolean;
  id: string;
  profile_image?: string;
}

export interface TutorProfile {
  id: string;
  academic_program: string;
  bio: string;
  phone: string;
  teaching_style: string;
  is_visible: boolean;
  approval_status: string;
  accepting_requests: boolean;
  profile_picture_url?: string;
  user: UserSummary;
}

/**
 * The user account behind a service's tutor. `ServiceTutor.id` is a *user* id,
 * not a tutor id - see `ServiceItem.tutor_id` for the tutor.
 */
export interface ServiceTutor extends UserSummary {}

export interface ServiceItem {
  id: string;
  /** The tutors row. Use this to address the tutor (profile, services, reviews). */
  tutor_id: string;
  /** The tutor's user account. Use this to address the person (chat). */
  tutor_user_id?: string;
  service_name: string;
  description: string;
  date: string;
  time: string;
  end_time?: string;
  price: number;
  level: string;
  joining_link: string;
  image_urls?: string[];
  tutor: ServiceTutor;
}

export interface TutorListResponse {
  success: boolean;
  message: string;
  metadata: unknown;
  data: TutorProfile[];
}

export interface ServiceListResponse {
  success: boolean;
  message: string;
  metadata: unknown;
  data: ServiceItem[];
}

export interface MediaItem {
  type: 'image' | 'video';
  url: string;
}

// The card-details step was removed: confirming a booking goes straight to the
// booking call, so there is no 'payment' state and no payment method to pick.
export type PaymentStep = 'review' | 'processing' | 'success' | 'error';