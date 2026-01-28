import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL + "/api";

// Processes
export const getProcesses = () => axios.get(`${API_URL}/processes`);
export const getProcess = (id) => axios.get(`${API_URL}/processes/${id}`);
export const createProcess = (data) => axios.post(`${API_URL}/processes`, data);
export const updateProcess = (id, data) => axios.put(`${API_URL}/processes/${id}`, data);
export const assignProcess = (id, consultorId, mediadorId) => 
  axios.post(`${API_URL}/processes/${id}/assign`, null, {
    params: { consultor_id: consultorId, mediador_id: mediadorId }
  });
export const getKanbanBoard = () => axios.get(`${API_URL}/processes/kanban`);
export const moveProcessKanban = (processId, newStatus) => 
  axios.put(`${API_URL}/processes/kanban/${processId}/move`, null, {
    params: { new_status: newStatus }
  });

// Deadlines
export const getDeadlines = (processId) => 
  axios.get(`${API_URL}/deadlines`, { params: { process_id: processId } });
export const getAllDeadlines = () => axios.get(`${API_URL}/deadlines`);
export const getMyDeadlines = () => axios.get(`${API_URL}/deadlines/my-deadlines`);
export const getCalendarDeadlines = (consultorId, mediadorId) => 
  axios.get(`${API_URL}/deadlines/calendar`, { 
    params: { consultor_id: consultorId, mediador_id: mediadorId } 
  });
export const createDeadline = (data) => axios.post(`${API_URL}/deadlines`, data);
export const updateDeadline = (id, data) => axios.put(`${API_URL}/deadlines/${id}`, data);
export const deleteDeadline = (id) => axios.delete(`${API_URL}/deadlines/${id}`);

// Users (Admin)
export const getUsers = (role) => 
  axios.get(`${API_URL}/users`, { params: { role } });
export const createUser = (data) => axios.post(`${API_URL}/users`, data);
export const updateUser = (id, data) => axios.put(`${API_URL}/users/${id}`, data);
export const deleteUser = (id) => axios.delete(`${API_URL}/users/${id}`);

// Stats
export const getStats = () => axios.get(`${API_URL}/stats`);

// Activities/Comments
export const getActivities = (processId) => 
  axios.get(`${API_URL}/activities`, { params: { process_id: processId } });
export const createActivity = (data) => axios.post(`${API_URL}/activities`, data);
export const deleteActivity = (id) => axios.delete(`${API_URL}/activities/${id}`);

// History
export const getHistory = (processId) => 
  axios.get(`${API_URL}/history`, { params: { process_id: processId } });

// Workflow Statuses
export const getWorkflowStatuses = () => axios.get(`${API_URL}/admin/workflow-statuses`);
export const createWorkflowStatus = (data) => axios.post(`${API_URL}/admin/workflow-statuses`, data);
export const updateWorkflowStatus = (id, data) => axios.put(`${API_URL}/admin/workflow-statuses/${id}`, data);
export const deleteWorkflowStatus = (id) => axios.delete(`${API_URL}/admin/workflow-statuses/${id}`);

// OneDrive Links (Manual)
export const getProcessOneDriveLinks = (processId) => 
  axios.get(`${API_URL}/onedrive/links/${processId}`);
export const addProcessOneDriveLink = (processId, data) => 
  axios.post(`${API_URL}/onedrive/links/${processId}`, data);
export const deleteProcessOneDriveLink = (processId, linkId) => 
  axios.delete(`${API_URL}/onedrive/links/${processId}/${linkId}`);

// OneDrive (Legacy - API based)
export const getOneDriveFiles = (folder) => 
  axios.get(`${API_URL}/onedrive/files`, { params: { folder } });
export const getClientOneDriveFiles = (clientName, subfolder) => 
  axios.get(`${API_URL}/onedrive/files/${encodeURIComponent(clientName)}`, { params: { subfolder } });
export const getOneDriveDownloadUrl = (itemId) => 
  axios.get(`${API_URL}/onedrive/download/${itemId}`);
export const getOneDriveStatus = () => axios.get(`${API_URL}/onedrive/status`);

// AI Document Analysis
export const analyzeDocument = (data) => axios.post(`${API_URL}/ai/analyze-document`, data);
export const analyzeOneDriveDocument = (data) => axios.post(`${API_URL}/ai/analyze-onedrive-document`, data);
export const getSupportedDocuments = () => axios.get(`${API_URL}/ai/supported-documents`);

// Document Expiry Management
export const getDocumentExpiries = (processId) => 
  axios.get(`${API_URL}/documents/expiry`, { params: { process_id: processId } });
export const getUpcomingExpiries = (days = 30) => 
  axios.get(`${API_URL}/documents/expiry/upcoming`, { params: { days } });
export const createDocumentExpiry = (data) => axios.post(`${API_URL}/documents/expiry`, data);
export const updateDocumentExpiry = (id, data) => axios.put(`${API_URL}/documents/expiry/${id}`, data);
export const deleteDocumentExpiry = (id) => axios.delete(`${API_URL}/documents/expiry/${id}`);
export const getDocumentTypes = () => axios.get(`${API_URL}/documents/types`);

// Alerts & Notifications
export const getNotifications = (unreadOnly = false) => 
  axios.get(`${API_URL}/alerts/notifications`, { params: { unread_only: unreadOnly } });
export const markNotificationRead = (id) => 
  axios.put(`${API_URL}/alerts/notifications/${id}/read`);
export const getProcessAlerts = (processId) => 
  axios.get(`${API_URL}/processes/${processId}/alerts`);
export const getAlertsByProcess = (processId) => 
  axios.get(`${API_URL}/alerts/process/${processId}`);
export const createDeedReminder = (processId, deedDate) => 
  axios.post(`${API_URL}/alerts/deed-reminder/${processId}`, null, { params: { deed_date: deedDate } });

// Admin - Impersonate
export const impersonateUser = (userId) => axios.post(`${API_URL}/admin/impersonate/${userId}`);
export const stopImpersonate = () => axios.post(`${API_URL}/admin/stop-impersonate`);

// Admin Users (CRUD completo)
export const getAdminUsers = (role) => axios.get(`${API_URL}/admin/users`, { params: { role } });
export const createAdminUser = (data) => axios.post(`${API_URL}/admin/users`, data);
export const updateAdminUser = (id, data) => axios.put(`${API_URL}/admin/users/${id}`, data);
export const deleteAdminUser = (id) => axios.delete(`${API_URL}/admin/users/${id}`);

// Tasks
export const getTasks = (params = {}) => axios.get(`${API_URL}/tasks`, { params });
export const getMyTasks = (includeCompleted = false) => 
  axios.get(`${API_URL}/tasks/my-tasks`, { params: { include_completed: includeCompleted } });
export const getProcessTasks = (processId) => 
  axios.get(`${API_URL}/tasks`, { params: { process_id: processId } });
export const createTask = (data) => axios.post(`${API_URL}/tasks`, data);
export const updateTask = (id, data) => axios.put(`${API_URL}/tasks/${id}`, data);
export const completeTask = (id) => axios.put(`${API_URL}/tasks/${id}/complete`);
export const reopenTask = (id) => axios.put(`${API_URL}/tasks/${id}/reopen`);
export const deleteTask = (id) => axios.delete(`${API_URL}/tasks/${id}`);

// Emails
export const getProcessEmails = (processId, direction = null) => 
  axios.get(`${API_URL}/emails/process/${processId}`, { params: { direction } });
export const getEmailStats = (processId) => axios.get(`${API_URL}/emails/stats/${processId}`);
export const createEmail = (data) => axios.post(`${API_URL}/emails`, data);
export const updateEmail = (id, data) => axios.put(`${API_URL}/emails/${id}`, data);
export const deleteEmail = (id) => axios.delete(`${API_URL}/emails/${id}`);
export const syncProcessEmails = (processId, days = 30) => 
  axios.post(`${API_URL}/emails/sync/${processId}`, null, { params: { days } });
export const sendEmailViaServer = (data) => axios.post(`${API_URL}/emails/send`, null, { params: data });
export const testEmailConnection = (account = null) => 
  axios.get(`${API_URL}/emails/test-connection`, { params: { account } });
export const getEmailAccounts = () => axios.get(`${API_URL}/emails/accounts`);
