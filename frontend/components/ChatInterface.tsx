'use client';

import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { documentsApi, searchApi } from '@/lib/api';
import { ChatMessage, SearchResponse, ROLE_ACCESS_MATRIX, UserRole } from '@/lib/types';
import { Send, Loader2, AlertTriangle, Shield, Route, Database, Clock, Target } from 'lucide-react';
import { formatResponseTime, formatConfidence, getRoleColor, getCollectionColor } from '@/lib/utils';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';

type RoleDocStatus = {
  isLoading: boolean;
  hasAnyAccessibleDocs: boolean;
  hasGeneralDocs: boolean;
  hasDepartmentDocs: boolean;
  notice: string | null;
};

const DEFAULT_ROLE_DOC_STATUS: RoleDocStatus = {
  isLoading: true,
  hasAnyAccessibleDocs: false,
  hasGeneralDocs: false,
  hasDepartmentDocs: false,
  notice: null,
};

interface MessageBubbleProps {
  message: ChatMessage;
  isLatest: boolean;
}

function MessageBubble({ message, isLatest }: MessageBubbleProps) {
  const { user } = useAuth();
  
  if (message.type === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-3xl bg-primary-600 text-white rounded-lg px-4 py-3 shadow-sm">
          <p className="text-sm leading-relaxed">{message.content}</p>
          <p className="text-xs text-primary-100 mt-2">
            {message.timestamp.toLocaleTimeString()}
          </p>
        </div>
      </div>
    );
  }

  const metadata = message.metadata;
  
  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-4xl w-full">
        {/* Main Response */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          {/* Header with route and role info */}
          {metadata && (
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 rounded-t-lg">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {metadata.semantic_route && (
                  <div className="flex items-center bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                    <Route className="w-3 h-3 mr-1" />
                    <span className="font-medium">{metadata.semantic_route}</span>
                  </div>
                )}
                
                {metadata.user_role && (
                  <div className={`flex items-center px-2 py-1 rounded-full ${getRoleColor(metadata.user_role)}`}>
                    <Shield className="w-3 h-3 mr-1" />
                    <span className="font-medium">{metadata.user_role.toUpperCase()}</span>
                  </div>
                )}
                
                {metadata.accessible_collections && (
                  <div className="flex items-center bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
                    <Database className="w-3 h-3 mr-1" />
                    <span>Access: {metadata.accessible_collections.join(', ')}</span>
                  </div>
                )}
                
                {metadata.confidence && (
                  <div className="flex items-center bg-green-100 text-green-800 px-2 py-1 rounded-full">
                    <Target className="w-3 h-3 mr-1" />
                    <span>{formatConfidence(metadata.confidence)}</span>
                  </div>
                )}
                
                {metadata.response_time_ms && (
                  <div className="flex items-center bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full">
                    <Clock className="w-3 h-3 mr-1" />
                    <span>{formatResponseTime(metadata.response_time_ms)}</span>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Warnings */}
          {metadata?.warnings && metadata.warnings.length > 0 && (
            <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
              {metadata.warnings.map((warning, index) => (
                <div key={index} className="flex items-start">
                  <AlertTriangle className="w-4 h-4 text-amber-600 mr-2 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-amber-800">{warning}</p>
                </div>
              ))}
            </div>
          )}
          
          {/* RBAC Message */}
          {metadata?.rbac_message && (
            <div className="px-4 py-3 bg-red-50 border-b border-red-200">
              <div className="flex items-start">
                <Shield className="w-4 h-4 text-red-600 mr-2 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-red-800">{metadata.rbac_message}</p>
              </div>
            </div>
          )}
          
          {/* Answer Content */}
          <div className="px-4 py-4">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            
            {/* Source Citations */}
            {metadata?.source_citations && metadata.source_citations.length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-100">
                <h4 className="text-xs font-semibold text-gray-700 mb-2">Sources:</h4>
                <div className="space-y-2">
                  {metadata.source_citations.map((citation, index) => (
                    <div key={index} className="flex items-center justify-between text-xs bg-gray-50 p-2 rounded">
                      <div className="flex items-center">
                        <span className="font-medium text-gray-900">{citation.document_name}</span>
                        {citation.page_number && (
                          <span className="ml-2 text-gray-500">• Page {citation.page_number}</span>
                        )}
                        {citation.section && (
                          <span className="ml-2 text-gray-500">• {citation.section}</span>
                        )}
                      </div>
                      <span className="text-gray-400">{formatConfidence(citation.relevance_score)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          {/* Timestamp */}
          <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 rounded-b-lg">
            <p className="text-xs text-gray-500">
              {message.timestamp.toLocaleTimeString()}
              {metadata?.guardrail_triggered && (
                <span className="ml-2 text-amber-600 font-medium">• Guardrail Active</span>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full typing-dot"></div>
          </div>
          <span className="text-sm text-gray-600">FinBot is thinking...</span>
        </div>
      </div>
    </div>
  );
}

export default function ChatInterface() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [roleDocStatus, setRoleDocStatus] = useState<RoleDocStatus>(DEFAULT_ROLE_DOC_STATUS);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatDisabled = !roleDocStatus.isLoading && !roleDocStatus.hasAnyAccessibleDocs;

  const getRoleLabel = (role: UserRole): string => {
    return role === 'c_level'
      ? 'Executive'
      : role.charAt(0).toUpperCase() + role.slice(1);
  };

  const getGeneralOnlyNotice = (role: UserRole): string => {
    if (role === 'c_level') {
      return 'Specialized documents are not available right now. You can ask only General queries like Company policies and general FAQs.';
    }

    return `${getRoleLabel(role)} documents are not available right now. You can ask only General queries like Company policies and general FAQs.`;
  };

  const getRoleExampleQueries = (role: UserRole): string[] => {
    switch (role) {
      case 'employee':
        return [
          '"What\'s our leave policy?"',
          '"What is the reimbursement process?"',
          '"Where can I find company holiday guidelines?"',
        ];
      case 'finance':
        return [
          '"Summarize our latest budget allocation."',
          '"Tell me about our Q3 performance."',
          '"What are the key financial highlights this quarter?"',
        ];
      case 'engineering':
        return [
          '"How do I deploy to production?"',
          '"What does the incident response runbook say?"',
          '"Show me the system architecture overview."',
        ];
      case 'marketing':
        return [
          '"Show me our brand guidelines."',
          '"What were the top campaign results this quarter?"',
          '"Give me a summary of competitor analysis."',
        ];
      case 'hr':
        return [
          '"What is the onboarding policy for new hires?"',
          '"How does the appraisal process work?"',
          '"Summarize the employee benefits policy."',
        ];
      case 'c_level':
        return [
          '"Give me an executive summary across all departments."',
          '"What are the top financial and operational risks?"',
          '"Summarize key updates from finance, engineering, and marketing."',
        ];
      default:
        return ['"What\'s our leave policy?"'];
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Add welcome message
    if (user && messages.length === 0) {
      const roleExamples = getRoleExampleQueries(user.role);
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        type: 'assistant',
        content: `👋 **Welcome to FinBot, ${user.full_name}!**

I'm your intelligent assistant for FinSolve Technologies. I can help you find information from our knowledge base while respecting your access permissions.

**Your Access Level:** ${user.role.toUpperCase()} - ${user.department}

**Available Collections:** ${user.role === 'c_level' ? 'All (finance, engineering, marketing, hr, general)' : 
  user.role === 'employee' ? 'General only' : 
  `${user.role}, general`}

**What I can do:**
- Answer questions from your accessible documents
- Provide source citations for all responses  
- Route queries to the right knowledge areas
- Apply safety guardrails to protect sensitive information

Try asking me something like:
- ${roleExamples[0]}
- ${roleExamples[1]}
- ${roleExamples[2]}

🛡️ **Security Note:** All queries are subject to role-based access control and safety guardrails.`,
        timestamp: new Date(),
        metadata: {
          user_role: user.role,
          accessible_collections: user.role === 'c_level' ? ['finance', 'engineering', 'marketing', 'hr', 'general'] :
                                  user.role === 'employee' ? ['general'] :
                                  [user.role, 'general'],
          semantic_route: 'system_welcome',
          source_citations: [],
          warnings: [],
          rbac_message: undefined,
          guardrail_triggered: false
        }
      };
      setMessages([welcomeMessage]);
    }
  }, [user, messages.length]);

  useEffect(() => {
    const loadRoleDocStatus = async () => {
      if (!user) {
        setRoleDocStatus(DEFAULT_ROLE_DOC_STATUS);
        return;
      }

      setRoleDocStatus((prev) => ({ ...prev, isLoading: true, notice: null }));

      try {
        const response = await documentsApi.getDocuments({
          page: 1,
            page_size: 100,
          upload_status: 'completed',
        });

        const documents = response.documents || [];
        const accessibleCollections = ROLE_ACCESS_MATRIX[user.role];
        const collectionCounts = documents.reduce((acc: Record<string, number>, doc: { collection: string }) => {
          acc[doc.collection] = (acc[doc.collection] || 0) + 1;
          return acc;
        }, {});

        const hasGeneralDocs = (collectionCounts.general || 0) > 0;
        const hasAnyAccessibleDocs = accessibleCollections.some((collection) => (collectionCounts[collection] || 0) > 0);

        let hasDepartmentDocs = false;
        if (user.role !== 'employee' && user.role !== 'c_level') {
          hasDepartmentDocs = (collectionCounts[user.role] || 0) > 0;
        } else if (user.role === 'c_level') {
          hasDepartmentDocs = ['finance', 'engineering', 'marketing', 'hr'].some(
            (collection) => (collectionCounts[collection] || 0) > 0
          );
        }

        let notice: string | null = null;
        if (!hasAnyAccessibleDocs) {
          notice = 'No documents are available for your role right now. Ask admin to upload documents before asking questions.';
          } else if (hasGeneralDocs && user.role !== 'employee' && user.role !== 'c_level' && !hasDepartmentDocs) {
          notice = getGeneralOnlyNotice(user.role);
        }

        setRoleDocStatus({
          isLoading: false,
          hasAnyAccessibleDocs,
          hasGeneralDocs,
          hasDepartmentDocs,
          notice,
        });
      } catch (error) {
        console.error('Failed to load document availability:', error);
        setRoleDocStatus({
          isLoading: false,
          hasAnyAccessibleDocs: false,
          hasGeneralDocs: false,
          hasDepartmentDocs: false,
          notice: 'Unable to verify document availability. Ask admin to upload documents if chat remains unavailable.',
        });
      }
    };

    loadRoleDocStatus();
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading || !user || chatDisabled || roleDocStatus.isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response: SearchResponse = await searchApi.search(inputValue.trim(), user.role);
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        metadata: {
          query: response.query,
          user_role: response.user_role,
          semantic_route: response.semantic_route,
          accessible_collections: response.accessible_collections,
          source_citations: response.source_citations,
          warnings: response.warnings,
          rbac_message: response.rbac_message || undefined,
          guardrail_triggered: response.guardrail_triggered,
          guardrail_info: response.guardrail_info,
          confidence: response.score,
          response_time_ms: response.response_time_ms
        }
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Show toast for guardrails or warnings
      if (response.guardrail_triggered && response.warnings.length > 0) {
        toast.error('Guardrail triggered: ' + response.warnings[0]);
      } else if (response.rbac_message) {
        toast.error('Access denied: ' + response.rbac_message);
      } else if (response.warnings.length > 0) {
        toast(response.warnings[0], { icon: '⚠️' });
      }

    } catch (error: any) {
      console.error('Search error:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant', 
        content: `❌ **Sorry, I encountered an error processing your request.**

${error.response?.data?.detail || error.message || 'Please try again or contact support if the issue persists.'}

**Troubleshooting:**
- Check if the backend server is running
- Verify your network connection
- Try a simpler query`,
        timestamp: new Date(),
        metadata: {
          user_role: user.role,
          warnings: ['System error occurred'],
          guardrail_triggered: true
        }
      };
      
      setMessages(prev => [...prev, errorMessage]);
      toast.error('Failed to get response from FinBot');
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  if (!user) {
    return <div>Please log in to use FinBot.</div>;
  }

  return (
    <div className="flex flex-col h-full">
      {roleDocStatus.notice && (
        <div className={`mx-4 mt-4 rounded-lg border px-4 py-3 text-sm ${chatDisabled ? 'border-red-200 bg-red-50 text-red-800' : 'border-amber-200 bg-amber-50 text-amber-800'}`}>
          <div className="flex items-start">
            <AlertTriangle className="mr-2 mt-0.5 h-4 w-4 flex-shrink-0" />
            <p>{roleDocStatus.notice}</p>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map((message, index) => (
          <div key={message.id} className="message-animate">
            <MessageBubble 
              message={message} 
              isLatest={index === messages.length - 1} 
            />
          </div>
        ))}
        
        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="border-t border-gray-200 bg-white px-4 py-4">
        <form onSubmit={handleSubmit} className="flex space-x-4">
          <div className="flex-1">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={chatDisabled ? 'Chat is disabled until documents are uploaded...' : 'Ask FinBot anything...'}
              disabled={isLoading || chatDisabled || roleDocStatus.isLoading}
              className="block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm px-4 py-3 pr-12"
            />
          </div>
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading || chatDisabled || roleDocStatus.isLoading}
            className="inline-flex items-center px-6 py-3 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </form>
        
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center space-x-4">
            <span>Role: <strong className="text-gray-700">{user.role.toUpperCase()}</strong></span>
            <span>Access: <strong className="text-gray-700">
              {user.role === 'c_level' ? 'All Collections' : 
               user.role === 'employee' ? 'General Only' : 
               `${user.role.charAt(0).toUpperCase() + user.role.slice(1)} + General`}
            </strong></span>
          </div>
          <span className="flex items-center">
            <Shield className="w-3 h-3 mr-1" />
            RBAC Enabled
          </span>
        </div>
      </div>
    </div>
  );
}