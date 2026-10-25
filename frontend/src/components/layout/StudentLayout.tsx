import React from 'react';
import { TopBar, TopBarProps } from './TopBar';
import { Sidebar } from './Sidebar';
import { MobileNavigation } from './MobileNavigation';
import { UserProfile } from '../../types';

export interface StudentLayoutProps extends Omit<TopBarProps, 'user'> {
  user: UserProfile;
  activePath: string;
  onNavigate: (path: string) => void;
  children: React.ReactNode;
}

export const StudentLayout: React.FC<StudentLayoutProps> = ({
  user,
  activePath,
  onNavigate,
  activeTerm,
  onTermChange,
  onLogout,
  onChangePasswordClick,
  onManageSessionsClick,
  onNotificationsClick,
  unreadNotificationsCount,
  children,
}) => {
  return (
    <div className="min-h-screen bg-bg flex flex-col text-navy font-sans">
      <TopBar
        user={user}
        activeTerm={activeTerm}
        onTermChange={onTermChange}
        onLogout={onLogout}
        onChangePasswordClick={onChangePasswordClick}
        onManageSessionsClick={onManageSessionsClick}
        onNotificationsClick={onNotificationsClick}
        unreadNotificationsCount={unreadNotificationsCount}
      />

      <MobileNavigation
        role={user.role}
        activePath={activePath}
        onNavigate={onNavigate}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          role={user.role}
          activePath={activePath}
          onNavigate={onNavigate}
          className="hidden lg:flex"
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full">
          {children}
        </main>
      </div>
    </div>
  );
};
