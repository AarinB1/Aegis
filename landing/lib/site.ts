const fallbackDashboardUrl = "https://aegis-dashboard-5k2w.onrender.com";

export const repoUrl = "https://github.com/AarinB1/Aegis";

export const dashboardUrl =
  process.env.NEXT_PUBLIC_DASHBOARD_URL?.trim() || fallbackDashboardUrl;
