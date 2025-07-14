import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { PiPencil, PiTrash, PiUserCircle, PiX, PiCheck } from 'react-icons/pi';
import Button from '../components/Button';
import InputText from '../components/InputText';
import Skeleton from '../components/Skeleton';
import useUsers from '../hooks/useUsers';
import ListPageLayout from '../layouts/ListPageLayout';
import { twMerge } from 'tailwind-merge';
import ButtonIcon from '../components/ButtonIcon';
import Help from '../components/Help';
import Alert from '../components/Alert';

// Dialog components
const DialogConfirmStatusChange: React.FC<{
  isOpen: boolean;
  userId: string;
  userName: string;
  currentStatus: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}> = ({ isOpen, userId, userName, currentStatus, onConfirm, onCancel, isLoading }) => {
  const { t } = useTranslation();
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg dark:bg-aws-squid-ink-dark">
        <h3 className="mb-4 text-lg font-bold">
          {currentStatus 
            ? t('admin.users.dialog.disableUser.title') 
            : t('admin.users.dialog.enableUser.title')}
        </h3>
        <p className="mb-6">
          {currentStatus 
            ? t('admin.users.dialog.disableUser.message', { userId, userName }) 
            : t('admin.users.dialog.enableUser.message', { userId, userName })}
        </p>
        <div className="flex justify-end gap-2">
          <Button outlined onClick={onCancel} disabled={isLoading}>
            {t('button.cancel')}
          </Button>
          <Button onClick={onConfirm} loading={isLoading}>
            {t('button.confirm')}
          </Button>
        </div>
      </div>
    </div>
  );
};

const DialogResetPassword: React.FC<{
  isOpen: boolean;
  userId: string;
  userName: string;
  onConfirm: (password: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}> = ({ isOpen, userId, userName, onConfirm, onCancel, isLoading }) => {
  const { t } = useTranslation();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const passwordsMatch = password === confirmPassword;
  const isValidPassword = password.length >= 8;
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg dark:bg-aws-squid-ink-dark">
        <h3 className="mb-4 text-lg font-bold">
          {t('admin.users.dialog.resetPassword.title')}
        </h3>
        <p className="mb-4">
          {t('admin.users.dialog.resetPassword.message', { userId, userName })}
        </p>
        
        <div className="mb-4">
          <InputText
            label={t('admin.users.dialog.resetPassword.newPassword')}
            type="password"
            value={password}
            onChange={setPassword}
            errorMessage={!isValidPassword && password ? t('admin.users.dialog.resetPassword.passwordTooShort') : undefined}
          />
        </div>
        
        <div className="mb-6">
          <InputText
            label={t('admin.users.dialog.resetPassword.confirmPassword')}
            type="password"
            value={confirmPassword}
            onChange={setConfirmPassword}
            errorMessage={!passwordsMatch && confirmPassword ? t('admin.users.dialog.resetPassword.passwordsDoNotMatch') : undefined}
          />
        </div>
        
        <Alert severity="warning" className="mb-4">
          {t('admin.users.dialog.resetPassword.warning')}
        </Alert>
        
        <div className="flex justify-end gap-2">
          <Button outlined onClick={onCancel} disabled={isLoading}>
            {t('button.cancel')}
          </Button>
          <Button 
            onClick={() => onConfirm(password)} 
            disabled={!passwordsMatch || !isValidPassword || isLoading}
            loading={isLoading}
          >
            {t('admin.users.dialog.resetPassword.resetButton')}
          </Button>
        </div>
      </div>
    </div>
  );
};

const AdminUserManagementPage: React.FC = () => {
  const { t } = useTranslation();
  const [nextToken, setNextToken] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const { users, nextToken: responseNextToken, isLoading, updateUserStatus, resetUserPassword, isUpdating, isResettingPassword } = useUsers(nextToken);
  
  // Dialog states
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<{ id: string; email: string; enabled: boolean } | null>(null);
  
  const handleStatusChange = useCallback((user: { id: string; email: string; enabled: boolean }) => {
    setSelectedUser(user);
    setStatusDialogOpen(true);
  }, []);
  
  const handleResetPassword = useCallback((user: { id: string; email: string }) => {
    setSelectedUser(user);
    setResetPasswordDialogOpen(true);
  }, []);
  
  const confirmStatusChange = useCallback(async () => {
    if (selectedUser) {
      await updateUserStatus(selectedUser.id, !selectedUser.enabled);
      setStatusDialogOpen(false);
    }
  }, [selectedUser, updateUserStatus]);
  
  const confirmResetPassword = useCallback(async (password: string) => {
    if (selectedUser) {
      const success = await resetUserPassword(selectedUser.id, password);
      if (success) {
        setResetPasswordDialogOpen(false);
      }
    }
  }, [selectedUser, resetUserPassword]);
  
  // Filter users based on search query
  const filteredUsers = searchQuery
    ? users.filter(user => 
        user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.id.toLowerCase().includes(searchQuery.toLowerCase()))
    : users;

  return (
    <>
      <DialogConfirmStatusChange
        isOpen={statusDialogOpen}
        userId={selectedUser?.id || ''}
        userName={selectedUser?.email || ''}
        currentStatus={selectedUser?.enabled || false}
        onConfirm={confirmStatusChange}
        onCancel={() => setStatusDialogOpen(false)}
        isLoading={isUpdating}
      />
      
      <DialogResetPassword
        isOpen={resetPasswordDialogOpen}
        userId={selectedUser?.id || ''}
        userName={selectedUser?.email || ''}
        onConfirm={confirmResetPassword}
        onCancel={() => setResetPasswordDialogOpen(false)}
        isLoading={isResettingPassword}
      />
      
      <ListPageLayout
        pageTitle={t('admin.users.title')}
        pageTitleHelp={t('admin.users.help')}
        searchCondition={
          <div className="mb-4">
            <InputText
              label={t('admin.users.search')}
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder={t('admin.users.searchPlaceholder')}
            />
          </div>
        }
        isLoading={isLoading}
        isEmpty={filteredUsers.length === 0}
        emptyMessage={searchQuery ? t('admin.users.noSearchResults') : t('admin.users.noUsers')}
      >
        <div className="overflow-x-auto">
          <table className="w-full table-auto border-collapse">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-2 text-left">{t('admin.users.table.email')}</th>
                <th className="px-4 py-2 text-left">{t('admin.users.table.id')}</th>
                <th className="px-4 py-2 text-left">{t('admin.users.table.status')}</th>
                <th className="px-4 py-2 text-left">{t('admin.users.table.created')}</th>
                <th className="px-4 py-2 text-left">{t('admin.users.table.groups')}</th>
                <th className="px-4 py-2 text-right">{t('admin.users.table.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr 
                  key={user.id} 
                  className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <td className="px-4 py-2">{user.email}</td>
                  <td className="px-4 py-2 font-mono text-sm">{user.id}</td>
                  <td className="px-4 py-2">
                    <span 
                      className={twMerge(
                        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                        user.enabled 
                          ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300" 
                          : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
                      )}
                    >
                      {user.enabled ? t('admin.users.status.enabled') : t('admin.users.status.disabled')}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm">{user.created_at}</td>
                  <td className="px-4 py-2">
                    <div className="flex flex-wrap gap-1">
                      {user.groups.map((group) => (
                        <span 
                          key={group.name}
                          className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-300"
                          title={group.description}
                        >
                          {group.name}
                        </span>
                      ))}
                      {user.groups.length === 0 && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {t('admin.users.noGroups')}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-2">
                      <ButtonIcon
                        onClick={() => handleStatusChange(user)}
                        title={user.enabled ? t('admin.users.actions.disable') : t('admin.users.actions.enable')}
                      >
                        {user.enabled ? <PiX /> : <PiCheck />}
                      </ButtonIcon>
                      <ButtonIcon
                        onClick={() => handleResetPassword(user)}
                        title={t('admin.users.actions.resetPassword')}
                      >
                        <PiPencil />
                      </ButtonIcon>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {responseNextToken && (
          <div className="mt-4 flex justify-center">
            <Button onClick={() => setNextToken(responseNextToken)}>
              {t('admin.users.loadMore')}
            </Button>
          </div>
        )}
      </ListPageLayout>
    </>
  );
};

export default AdminUserManagementPage;