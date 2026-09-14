// src/services/dashboard.service.ts
// Dashboard and admin stats API calls

import api from "./api";
import type { ApiResponse, DashboardStats } from "../types";

import adminService from "./admin.service";

const dashboardService = {
  async getSupportStats(): Promise<DashboardStats> {
    const { data } = await api.get<ApiResponse<DashboardStats>>(
      "/api/v1/dashboard/stats"
    );
    return data.data;
  },

  async getAdminStats(): Promise<any> {
    return adminService.getDashboardData();
  },
};

export default dashboardService;
