import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  pagination?: {
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
    totalItems?: number;
    itemsPerPage?: number;
  };
  isLoading?: boolean;
}

export function Table<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyMessage = 'No records found',
  pagination,
  isLoading = false,
}: TableProps<T>) {
  return (
    <div className="w-full bg-surface border border-border rounded-xl shadow-subtle overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse" role="table">
          <thead>
            <tr className="border-b border-border bg-bg/60 text-navy-muted uppercase tracking-wider text-xs font-semibold">
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={`px-4 py-3 select-none ${col.className || ''} ${
                    col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                  }`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-navy-subtle">
                  <div className="inline-flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-teal animate-ping" />
                    <span>Loading data...</span>
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-navy-subtle">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item) => (
                <tr
                  key={keyExtractor(item)}
                  onClick={() => onRowClick?.(item)}
                  className={`transition-colors hover:bg-bg/40 ${
                    onRowClick ? 'cursor-pointer' : ''
                  }`}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-4 py-3 text-navy ${col.className || ''} ${
                        col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                      }`}
                    >
                      {col.render ? col.render(item) : ((item as any)[col.key] as React.ReactNode)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pagination && pagination.totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-bg/30 text-xs text-navy-subtle">
          <div>
            {pagination.totalItems !== undefined ? (
              <span>
                Page <strong className="text-navy">{pagination.currentPage}</strong> of{' '}
                <strong className="text-navy">{pagination.totalPages}</strong> ({pagination.totalItems} total items)
              </span>
            ) : (
              <span>
                Page <strong className="text-navy">{pagination.currentPage}</strong> of{' '}
                <strong className="text-navy">{pagination.totalPages}</strong>
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={pagination.currentPage <= 1}
              onClick={() => pagination.onPageChange(pagination.currentPage - 1)}
              leftIcon={<ChevronLeft className="w-4 h-4" />}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={pagination.currentPage >= pagination.totalPages}
              onClick={() => pagination.onPageChange(pagination.currentPage + 1)}
              rightIcon={<ChevronRight className="w-4 h-4" />}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
