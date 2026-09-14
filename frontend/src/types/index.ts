// src/types/index.ts
// All shared TypeScript types matching the backend schemas

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "customer" | "support" | "admin";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

// ── Category / Seller ─────────────────────────────────────────────────────────
export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon: string;
}

export interface Seller {
  id: string;
  name: string;
  slug: string;
  rating: number;
  is_verified: boolean;
  city: string;
}

// ── Products ──────────────────────────────────────────────────────────────────
export interface ProductImage {
  id: string;
  image_url: string;
  alt_text?: string;
  sort_order: number;
  is_primary: boolean;
}

export interface ProductListItem {
  id: string;
  name: string;
  slug: string;
  brand?: string;
  price: number;
  original_price?: number;
  discount_percent: number;
  rating: number;
  review_count: number;
  image_url?: string;
  stock: number;
  category?: Category;
  seller?: Seller;
  images: ProductImage[];
}

export interface Product extends ProductListItem {
  description: string;
  sku: string;
  specifications?: Record<string, string>;
  is_active: boolean;
  created_at: string;
}

export interface PaginatedProducts {
  items: ProductListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}


// ── Orders ────────────────────────────────────────────────────────────────────
export interface OrderListItem {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  created_at: string;
  item_count: number;
}

export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string;
  product_sku?: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface Payment {
  id: string;
  amount: number;
  status: string;
  method: string;
  paid_at?: string;
}

export interface ReturnRequest {
  id: string;
  reason: string;
  status: string;
  created_at: string;
}

export interface Order {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  tracking_number?: string;
  estimated_delivery?: string;
  delivered_at?: string;
  notes?: string;
  created_at: string;
  items: OrderItem[];
  payment?: Payment;
  return_request?: ReturnRequest;
}

export interface PaginatedOrders {
  items: OrderListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ── Tickets ───────────────────────────────────────────────────────────────────
export type TicketStatus =
  | "open"
  | "assigned"
  | "in_progress"
  | "waiting_for_customer"
  | "waiting"
  | "resolved"
  | "closed"
  | "reopened";

export type TicketPriority = "low" | "medium" | "high" | "urgent";

export interface TicketListItem {
  id: string;
  ticket_number: string;
  subject: string;
  priority: TicketPriority;
  status: TicketStatus;
  assigned_to?: string;
  sla_deadline?: string;
  created_at: string;
  updated_at?: string;
}

export interface TicketNote {
  id: string;
  ticket_id: string;
  author_id?: string;
  author_name?: string;
  content: string;
  edit_history?: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
}

export interface TicketReply {
  id: string;
  ticket_id: string;
  author_id?: string;
  author_type: string;
  author_name?: string;
  content: string;
  attachment_placeholder?: string;
  is_ai_summary: boolean;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  event_type: string;
  actor_id?: string;
  actor_label?: string;
  message: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface AISummary {
  issue_summary?: string;
  customer_intent?: string;
  relevant_orders?: string[];
  products_mentioned?: string[];
  suggested_resolution?: string;
  retrieved_knowledge?: Record<string, unknown>[];
  confidence_score?: number;
  selected_agent?: string;
  escalation_reason?: string;
}

export interface TicketDetail {
  id: string;
  ticket_number: string;
  subject: string;
  description: string;
  priority: TicketPriority;
  status: TicketStatus;
  customer_id: string;
  customer_name?: string;
  customer_email?: string;
  customer_user_id?: string;
  customer_total_orders?: number;
  customer_total_spent?: number;
  order_id?: string;
  order_number?: string;
  order_status?: string;
  order_payment_status?: string;
  order_total_amount?: number;
  conversation_id?: string;
  assigned_to?: string;
  assigned_agent_name?: string;
  assigned_at?: string;
  last_updated_by?: string;
  resolved_at?: string;
  closed_at?: string;
  first_response_at?: string;
  resolution_time_seconds?: number;
  sla_deadline?: string;
  intent?: string;
  confidence?: number;
  escalation_reason?: string;
  ai_summary?: AISummary;
  notes: TicketNote[];
  replies: TicketReply[];
  timeline: TimelineEvent[];
  created_at: string;
  updated_at: string;
}

export interface PaginatedTickets {
  items: TicketListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// ── Dashboard / Analytics ─────────────────────────────────────────────────────
export interface DashboardStats {
  open_tickets: number;
  assigned_tickets: number;
  resolved_today: number;
  urgent_tickets: number;
  average_response_time_seconds?: number;
  average_resolution_time_seconds?: number;
  customer_satisfaction?: number;
  agent_workload: Record<string, unknown>[];
  escalations: number;
  ai_resolution_percent?: number;
  human_resolution_percent?: number;
  total_tickets: number;
  closed_tickets: number;
  waiting_for_customer: number;
}

// ── Admin Console Data Types ──────────────────────────────────────────────────
export interface RecentOrderSummary {
  id: string;
  order_number: string;
  customer_name: string;
  customer_email: string;
  total_amount: number;
  status: string;
  created_at: string;
  item_count: number;
}

export interface RecentUserSummary {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  total_orders: number;
  total_spent: number;
}

export interface LowStockProductSummary {
  id: string;
  name: string;
  sku: string;
  brand?: string;
  price: number;
  stock: number;
  category_name?: string;
  primary_image_url?: string;
}

export interface RecentTicketSummary {
  id: string;
  ticket_number: string;
  subject: string;
  customer_name: string;
  priority: string;
  status: string;
  created_at: string;
}

export interface AdminDashboardData {
  total_users: number;
  total_customers: number;
  total_products: number;
  total_orders: number;
  total_revenue: number;
  pending_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  total_tickets: number;
  open_tickets: number;
  urgent_tickets: number;
  resolved_tickets: number;
  ai_resolution_rate: number;
  average_response_time_seconds?: number;
  average_resolution_time_seconds?: number;
  low_stock_products_count: number;
  out_of_stock_products_count: number;
  recent_orders: RecentOrderSummary[];
  recent_users: RecentUserSummary[];
  low_stock_products: LowStockProductSummary[];
  recent_tickets: RecentTicketSummary[];
  order_status_distribution: { name: string; value: number }[];
  ticket_status_distribution: { name: string; value: number }[];
  revenue_by_day: { date: string; revenue: number }[];
}

export interface AdminUserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  customer_id?: string;
  phone?: string;
  total_orders: number;
  total_spent: number;
  total_tickets: number;
  open_tickets: number;
}

export interface PaginatedAdminUsers {
  items: AdminUserItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminUserDetail {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  customer_id?: string;
  phone?: string;
  avatar_url?: string;
  loyalty_points: number;
  shipping_addresses: Record<string, any>[];
  total_orders: number;
  total_spent: number;
  total_tickets: number;
  open_tickets: number;
  orders: Record<string, any>[];
  tickets: Record<string, any>[];
}

export interface AdminProductItem {
  id: string;
  name: string;
  slug: string;
  sku: string;
  brand?: string;
  category_id?: string;
  category_name?: string;
  price: number;
  original_price?: number;
  discount_percent: number;
  stock: number;
  rating: number;
  review_count: number;
  is_active: boolean;
  primary_image_url?: string;
  units_sold: number;
  total_revenue: number;
  created_at: string;
}

export interface PaginatedAdminProducts {
  items: AdminProductItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminProductDetail {
  id: string;
  name: string;
  slug: string;
  sku: string;
  brand?: string;
  description: string;
  category_id?: string;
  category_name?: string;
  seller_name?: string;
  price: number;
  original_price?: number;
  discount_percent: number;
  stock: number;
  rating: number;
  review_count: number;
  is_active: boolean;
  specifications?: Record<string, any>;
  images: Record<string, any>[];
  units_sold: number;
  total_revenue: number;
  recent_orders: Record<string, any>[];
  created_at: string;
}

export interface AdminOrderItem {
  id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  customer_email: string;
  status: string;
  payment_method?: string;
  payment_status?: string;
  total_amount: number;
  item_count: number;
  created_at: string;
}

export interface PaginatedAdminOrders {
  items: AdminOrderItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminOrderDetail {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  tracking_number?: string;
  estimated_delivery?: string;
  delivered_at?: string;
  notes?: string;
  created_at: string;
  customer: Record<string, any>;
  shipping_address?: Record<string, any>;
  items: OrderItem[];
  payment?: Record<string, any>;
  return_request?: Record<string, any>;
  tickets: Record<string, any>[];
}

export interface AdminAnalyticsData {
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  revenue_trend: { date: string; revenue: number }[];
  orders_trend: { date: string; orders: number }[];
  best_selling_products: { name: string; units_sold: number; revenue: number }[];
  sales_by_category: { name: string; revenue: number }[];
  stock_status_summary: { in_stock: number; low_stock: number; out_of_stock: number };
  total_customers: number;
  new_customers_30d: number;
  repeat_customer_rate: number;
  average_customer_spend: number;
  total_tickets: number;
  open_tickets: number;
  resolution_rate: number;
  ai_resolution_rate: number;
  average_response_time_seconds?: number;
  average_resolution_time_seconds?: number;
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export interface ChatCitation {
  source?: string;
  title?: string;
  content?: string;
  relevance?: number;
  score?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: ChatCitation[];
  intent?: string;
  agent?: string;
  confidence?: number;
  isTyping?: boolean;
  error?: boolean;
}

export interface ChatConversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  messages: ChatMessage[];
}

// ── API Response wrapper ──────────────────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}
