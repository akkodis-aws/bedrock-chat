import useSWR from 'swr';
import { fetcher } from '../utils/Fetcher';
import { User } from './useUsers';

const useUserDetails = (userId?: string) => {
  const { data, error, isLoading, mutate } = useSWR<User>(
    userId ? `/admin/users/${userId}` : null,
    fetcher
  );

  return {
    user: data,
    isLoading,
    error,
    refresh: mutate,
  };
};

export default useUserDetails;