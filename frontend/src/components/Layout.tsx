import type { FC } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import './Layout.css';

export const Layout: FC = () => {
  return (
    <div className="layout">
      <Sidebar />
      <div className="layout-content-wrapper">
        <main className="layout-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
