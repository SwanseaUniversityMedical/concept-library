import { DashboardService } from './dashboard.js';

domReady.finally(() => {
  window.Dashboard = new DashboardService();
});
