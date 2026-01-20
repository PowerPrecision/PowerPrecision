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

// Deadlines
export const getDeadlines = (processId) => 
  axios.get(`${API_URL}/deadlines`, { params: { process_id: processId } });
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
export const getWorkflowStatuses = () => axios.get(`${API_URL}/workflow-statuses`);
export const createWorkflowStatus = (data) => axios.post(`${API_URL}/workflow-statuses`, data);
export const updateWorkflowStatus = (id, data) => axios.put(`${API_URL}/workflow-statuses/${id}`, data);
export const deleteWorkflowStatus = (id) => axios.delete(`${API_URL}/workflow-statuses/${id}`);

// OneDrive
export const getOneDriveFiles = (folder) => 
  axios.get(`${API_URL}/onedrive/files`, { params: { folder } });
export const getClientOneDriveFiles = (clientName, subfolder) => 
  axios.get(`${API_URL}/onedrive/files/${encodeURIComponent(clientName)}`, { params: { subfolder } });
export const getOneDriveDownloadUrl = (itemId) => 
  axios.get(`${API_URL}/onedrive/download/${itemId}`);
export const getOneDriveStatus = () => axios.get(`${API_URL}/onedrive/status`);
