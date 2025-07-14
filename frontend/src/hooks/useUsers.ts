import { useState } from 'react';
import useSWR from 'swr';
import { fetcher } from '../utils/Fetcher';
import useSnackbar from './useSnackbar';
import { useTranslation } from 'react-i18next';

export interface UserGroup {
  name: string;
  description: string;
}

export interface User {
  id: string;
  email: string;
  enabled: boolean;
  created_at: string;
  last_modified: string;
  groups: UserGroup[];
}

export interface UsersResponse {
  users: User[];
  next_token: string | null;
}

const useUsers = (nextToken?: string, limit: number = 50) => {
  const { t } = useTranslation();
  const { open } = useSnackbar();
  const [isUpdating, setIsUpdating] = useState(false);
  const [isResettingPassword, setIsResettingPassword] = useState(false);

  // Construct the URL with query parameters
  const url = `/admin/users${nextToken ? `?next_token=${nextToken}` : ''}${limit ? `${nextToken ? '&' : '?'}limit=${limit}` : ''}`;
  
  const { data, error, isLoading, mutate } = useSWR<UsersResponse>(
    url,
    fetcher
  );

  const updateUserStatus = async (userId: string, enabled: boolean): Promise<boolean> => {
    setIsUpdating(true);
    try {
      const response = await fetch(`/admin/users/${userId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update user status');
      }

      await mutate();
      open(t('admin.users.notification.statusUpdateSuccess'));
      return true;
    } catch (error) {
      console.error('Error updating user status:', error);
      open(t('admin.users.notification.statusUpdateError'));
      return false;
    } finally {
      setIsUpdating(false);
    }
  };

  const resetUserPassword = async (userId: string, temporaryPassword: string): Promise<boolean> => {
    setIsResettingPassword(true);
    try {
      const response = await fetch(`/admin/users/${userId}/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ temporary_password: temporaryPassword }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to reset user password');
      }

      open(t('admin.users.notification.passwordResetSuccess'));
      return true;
    } catch (error) {
      console.error('Error resetting user password:', error);
      open(t('admin.users.notification.passwordResetError'));
      return false;
    } finally {
      setIsResettingPassword(false);
    }
  };

  return {
    users: data?.users || [],
    nextToken: data?.next_token || null,
    isLoading,
    error,
    isUpdating,
    isResettingPassword,
    updateUserStatus,
    resetUserPassword,
    refresh: mutate,
  };
};

export default useUsers;