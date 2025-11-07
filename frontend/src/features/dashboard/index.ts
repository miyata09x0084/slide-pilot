// 通常import用
export { default as DashboardPage } from './DashboardPage';
export { dashboardLoader } from './loaders/dashboardLoader';

// React Router lazy loading用
export { dashboardLoader as lazyDashboardLoader } from './loaders/dashboardLoader';
export { default as lazyDashboardComponent } from './DashboardPage';
