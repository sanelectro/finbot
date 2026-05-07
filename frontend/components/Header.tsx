'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { useRouter, usePathname } from 'next/navigation';
import { 
  Building2, 
  LogOut, 
  User, 
  Settings, 
  MessageSquare, 
  Shield, 
  Database,
  Menu,
  X
} from 'lucide-react';
import { getRoleColor } from '@/lib/utils';
import toast from 'react-hot-toast';

interface HeaderProps {
  onMobileMenuToggle?: () => void;
  isMobileMenuOpen?: boolean;
  refreshCountdown?: number;
  isRefreshing?: boolean;
}

export default function Header({ onMobileMenuToggle, isMobileMenuOpen, refreshCountdown, isRefreshing }: HeaderProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully');
    router.push('/login');
  };

  const navigation = [
    { name: 'Chat', href: '/chat', icon: MessageSquare, current: pathname === '/chat' },
    { name: 'Admin', href: '/admin', icon: Settings, current: pathname.startsWith('/admin'), adminOnly: true },
  ];

  const filteredNavigation = navigation.filter(item => 
    !item.adminOnly || (user?.role === 'c_level')
  );

  if (!user) {
    return null;
  }

  return (
    <header className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center py-4">
        {/* Left side - Logo and Navigation */}
        <div className="flex items-center">
          {/* Mobile menu button */}
          <button
            type="button"
            className="md:hidden -ml-2 mr-2 p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
            onClick={onMobileMenuToggle}
          >
            {isMobileMenuOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </button>

          {/* Logo */}
          <div className="flex items-center">
            <div className="flex items-center justify-center w-8 h-8 bg-primary-600 rounded-lg mr-3">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">FinBot</h1>
              <p className="text-xs text-gray-500">FinSolve Technologies</p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex ml-8 space-x-1">
            {filteredNavigation.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.name}
                  onClick={() => router.push(item.href)}
                  className={`${
                    item.current
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  } px-3 py-2 rounded-lg text-sm font-medium flex items-center transition-colors`}
                >
                  <Icon className="w-4 h-4 mr-2" />
                  {item.name}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Right side - User info and actions */}
        <div className="flex items-center space-x-4">
          {/* Auto-refresh countdown */}
          {refreshCountdown !== undefined && (
            <div className="text-sm text-gray-500 px-3 py-1 rounded-lg bg-gray-50">
              {isRefreshing ? 'Refreshing...' : `Auto refreshes in ${refreshCountdown}s`}
            </div>
          )}

          {/* Role Badge */}
          <div className={`hidden sm:flex items-center px-3 py-1 rounded-full text-sm font-medium ${getRoleColor(user.role)}`}>
            <Shield className="w-4 h-4 mr-1" />
            {user.role.toUpperCase()}
          </div>

          {/* User Menu */}
          <div className="relative">
            <button
              type="button"
              className="flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-primary-600" />
                </div>
                <div className="hidden md:block text-left">
                  <p className="text-sm font-medium text-gray-700">{user.full_name}</p>
                  <p className="text-xs text-gray-500">{user.department}</p>
                </div>
              </div>
            </button>

            {/* Dropdown Menu */}
            {showUserMenu && (
              <>
                <div 
                  className="fixed inset-0 z-10" 
                  onClick={() => setShowUserMenu(false)}
                ></div>
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-20">
                  <div className="px-4 py-3 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                    <p className="text-sm text-gray-500">{user.email}</p>
                    <div className="mt-2 flex items-center space-x-2">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getRoleColor(user.role)}`}>
                        {user.role.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">• {user.department}</span>
                    </div>
                  </div>
                  
                  <div className="py-2">
                    <div className="px-4 py-2">
                      <div className="text-xs font-semibold text-gray-700 mb-2">Access Level:</div>
                      <div className="space-y-1">
                        {user.role === 'c_level' ? (
                          <div className="flex items-center text-xs text-gray-600">
                            <Database className="w-3 h-3 mr-2" />
                            All Collections (Executive)
                          </div>
                        ) : user.role === 'employee' ? (
                          <div className="flex items-center text-xs text-gray-600">
                            <Database className="w-3 h-3 mr-2" />
                            General Only
                          </div>
                        ) : (
                          <>
                            <div className="flex items-center text-xs text-gray-600">
                              <Database className="w-3 h-3 mr-2" />
                              {user.role.charAt(0).toUpperCase() + user.role.slice(1)} Department
                            </div>
                            <div className="flex items-center text-xs text-gray-600">
                              <Database className="w-3 h-3 mr-2" />
                              General Policies
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-gray-100 pt-2">
                    <button
                      onClick={handleLogout}
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <LogOut className="w-4 h-4 mr-3" />
                      Sign out
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Navigation Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-gray-200">
          <div className="px-2 py-3 space-y-1">
            {filteredNavigation.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.name}
                  onClick={() => {
                    router.push(item.href);
                    onMobileMenuToggle?.();
                  }}
                  className={`${
                    item.current
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  } group flex items-center px-3 py-2 text-sm font-medium rounded-lg w-full`}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {item.name}
                </button>
              );
            })}
          </div>
          
          {/* Mobile Role Info */}
          <div className="border-t border-gray-200 px-4 py-3">
            <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getRoleColor(user.role)}`}>
              <Shield className="w-4 h-4 mr-1" />
              {user.role.toUpperCase()} ACCESS
            </div>
          </div>
        </div>
      )}
    </header>
  );
}