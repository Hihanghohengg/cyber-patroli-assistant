import axios from 'axios';
import {
  OverviewStats,
  TrendingTopicItem,
  TrendingDetail,
  ContentItem,
  ContentDetail,
  User,
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '';

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/dashboard`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiV1 = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

const attachInterceptors = (instance: typeof api) => {
  instance.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (
        error.response?.status === 401 &&
        !window.location.hash.includes('/login') &&
        !window.location.pathname.includes('/login')
      ) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.hash = '#/login';
      }
      return Promise.reject(error);
    }
  );
};

attachInterceptors(api);
attachInterceptors(apiV1);

export const apiClient = {
  auth: {
    login: async (username: string, password: string) => {
      const res = await api.post<{ access_token: string; user: User }>('/auth/login', {
        username,
        password,
      });
      return res.data;
    },
    getMe: async () => {
      const res = await api.get<User>('/auth/me');
      return res.data;
    },
  },
  overview: {
    get: async () => {
      const res = await api.get<OverviewStats>('/overview');
      return res.data;
    },
  },
  trending: {
    list: async (params?: { category?: string; search?: string; status?: string; limit?: number }) => {
      const res = await api.get<TrendingTopicItem[]>('/trending', { params });
      return res.data;
    },
    get: async (issueId: string) => {
      const res = await api.get<TrendingDetail>(`/trending/${issueId}`);
      return res.data;
    },
    getContents: async (issueId: string) => {
      const res = await api.get<ContentItem[]>(`/trending/${issueId}/contents`);
      return res.data;
    },
    recalculate: async () => {
      const res = await api.post<{ status: string; message: string }>('/trending/recalculate');
      return res.data;
    },
  },
  contents: {
    list: async (params?: {
      platform?: string;
      category?: string;
      sentiment?: string;
      risk_level?: string;
      status?: string;
      search?: string;
      skip?: number;
      limit?: number;
    }) => {
      const res = await api.get<ContentItem[]>('/contents', { params });
      return res.data;
    },
    get: async (contentId: string) => {
      const res = await api.get<ContentDetail>(`/contents/${contentId}`);
      return res.data;
    },
    verifyEvidence: async (contentId: string) => {
      const res = await api.get<any>(`/contents/${contentId}/verify-evidence`);
      return res.data;
    },
  },
  validation: {
    validate: async (
      contentId: string,
      payload: {
        status: string;
        notes?: string;
        risk_level_override?: string;
        category_override?: string;
      }
    ) => {
      const res = await api.post(`/contents/${contentId}/validate`, payload);
      return res.data;
    },
    reclassify: async (
      contentId: string,
      payload: {
        category?: string;
        issue_id?: string;
      }
    ) => {
      const res = await api.post(`/contents/${contentId}/reclassify`, payload);
      return res.data;
    },
  },
  analytics: {
    getTimeseries: async (days: number = 7) => {
      const res = await api.get<any[]>('/analytics/timeseries', { params: { days } });
      return res.data;
    },
    getPlatforms: async () => {
      const res = await api.get<any[]>('/analytics/platforms');
      return res.data;
    },
    getSentiments: async () => {
      const res = await api.get<any[]>('/analytics/sentiments');
      return res.data;
    },
  },
  v1: {
    getSummary: async (params?: {
      date_from?: string;
      date_to?: string;
      platform?: string;
      category?: string;
      risk_level?: string;
    }) => {
      const res = await apiV1.get<any>('/dashboard/summary', { params });
      return res.data;
    },
    getTimeseries: async (params?: {
      date_from?: string;
      date_to?: string;
      interval?: string;
      metric?: string;
    }) => {
      const res = await apiV1.get<any>('/dashboard/timeseries', { params });
      return res.data;
    },
    getBreakdown: async (params?: { dimension?: string; date_from?: string; date_to?: string }) => {
      const res = await apiV1.get<any>('/dashboard/breakdown', { params });
      return res.data;
    },
    getTop: async (dimension: 'topics' | 'actors' | 'sources', limit: number = 10) => {
      const res = await apiV1.get<any>('/dashboard/top', { params: { dimension, limit } });
      return res.data;
    },
    getReports: async (params?: {
      page?: number;
      limit?: number;
      category?: string;
      risk?: string;
      platform?: string;
      status?: string;
      search?: string;
    }) => {
      const res = await apiV1.get<any>('/dashboard/reports', { params });
      return res.data;
    },
    exportBlob: async (format: 'csv' | 'json' = 'csv', params?: any) => {
      const res = await apiV1.get('/dashboard/export', {
        params: { ...params, format },
        responseType: 'blob',
      });
      const blob = new Blob([res.data], {
        type: format === 'csv' ? 'text/csv;charset=utf-8;' : 'application/json;charset=utf-8;',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `rekap_patroli_siber_${new Date().toISOString().slice(0, 10)}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
    exportUrl: (format: 'csv' | 'json') => {
      return `${API_BASE_URL}/api/v1/dashboard/export?format=${format}`;
    },
  },
  admin: {
    listKnowledge: async (params?: { page?: number; limit?: number; category?: string; decision?: string; search?: string }) => {
      const res = await apiV1.get<any>('/admin/knowledge', { params });
      return res.data;
    },
    getKnowledge: async (id: string) => {
      const res = await apiV1.get<any>(`/admin/knowledge/${id}`);
      return res.data;
    },
    createKnowledge: async (payload: any) => {
      const res = await apiV1.post<any>('/admin/knowledge', payload);
      return res.data;
    },
    updateKnowledge: async (id: string, payload: any) => {
      const res = await apiV1.put<any>(`/admin/knowledge/${id}`, payload);
      return res.data;
    },
    deleteKnowledge: async (id: string) => {
      const res = await apiV1.delete<any>(`/admin/knowledge/${id}`);
      return res.data;
    },
    listEntities: async (params?: { entity_type?: string; status?: string; search?: string; page?: number; limit?: number }) => {
      const res = await apiV1.get<any>('/admin/entities', { params });
      return res.data;
    },
    mergeEntities: async (sourceId: string, targetId: string) => {
      const res = await apiV1.post<any>('/admin/entities/merge', { source_id: sourceId, target_id: targetId });
      return res.data;
    },
    approveEntity: async (id: string) => {
      const res = await apiV1.put<any>(`/admin/entities/${id}/approve`);
      return res.data;
    },
    addAlias: async (id: string, alias: string) => {
      const res = await apiV1.post<any>(`/admin/entities/${id}/aliases`, { alias });
      return res.data;
    },
    listUsers: async () => {
      const res = await apiV1.get<any[]>('/admin/users');
      return res.data;
    },
    listPatrolUsers: async () => {
      const res = await apiV1.get<any[]>('/admin/patrol-users');
      return res.data;
    },
    createOrUpdatePatrolUser: async (payload: { telegram_id: number; full_name: string; role: string }) => {
      const res = await apiV1.post<any>('/admin/patrol-users', payload);
      return res.data;
    },
    updatePatrolUser: async (id: string, payload: { role?: string; full_name?: string; is_active?: boolean }) => {
      const res = await apiV1.put<any>(`/admin/patrol-users/${id}`, payload);
      return res.data;
    },
    deactivatePatrolUser: async (id: string) => {
      const res = await apiV1.delete<any>(`/admin/patrol-users/${id}`);
      return res.data;
    },
    listAudit: async (params?: { page?: number; limit?: number; action?: string }) => {
      const res = await apiV1.get<any>('/admin/audit', { params });
      return res.data;
    },
  },
  assistant: {
    intake: async (payload: {
      url: string;
      source_channel?: string;
      reporter_identifier?: string;
      notes?: string;
      screenshot_base64?: string;
      media_image_url?: string;
    }) => {
      const res = await apiV1.post<any>('/assistant/intake', payload);
      return res.data;
    },
  },
};


