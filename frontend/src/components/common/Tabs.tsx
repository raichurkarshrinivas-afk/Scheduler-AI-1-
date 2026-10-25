import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className = '' }) => {
  return (
    <div className={`border-b border-border ${className}`} role="tablist">
      <nav className="-mb-px flex space-x-6 overflow-x-auto" aria-label="Tabs">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => onChange(tab.id)}
              className={`flex items-center gap-2 py-3 px-1 border-b-2 text-sm font-medium transition-colors whitespace-nowrap select-none focus-visible:outline-2 focus-visible:outline-teal ${
                isActive
                  ? 'border-teal text-teal'
                  : 'border-transparent text-navy-muted hover:text-navy hover:border-border-strong'
              }`}
            >
              {tab.icon && <span aria-hidden="true">{tab.icon}</span>}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={`ml-1 text-xs py-0.5 px-2 rounded-full font-semibold ${
                    isActive ? 'bg-teal-light text-teal' : 'bg-bg text-navy-subtle'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
};
