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
