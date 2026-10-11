
import { useState, type FormEvent } from 'react'
import './App.css'
import {
  login,
  getCurrentUser,
  createConversation,
  streamChat,
  getConversations,
  getConversation,
  type User,
  type ChatSource,
  type Conversation,
} from './services/api'

type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

function App() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loginError, setLoginError] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)

  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [historyError, setHistoryError] = useState('')

  const [isSending, setIsSending] = useState(false)
  const [chatError, setChatError] = useState('')
  const [activeSection, setActiveSection] = useState<'chat' | 'documents'>('chat')

  async function loadConversations(token: string) {
    setIsLoadingHistory(true)
    setHistoryError('')

    try {
      const data = await getConversations(token)
      setConversations(data)
    } catch (error) {
      setHistoryError(
        error instanceof Error
          ? error.message
          : 'Unable to load conversation history.',
      )
    } finally {
      setIsLoadingHistory(false)
    }
  }

  async function handleSelectConversation(conversationId: number) {
    if (!accessToken || isSending) return

    setChatError('')
    setHistoryError('')
    setActiveSection('chat')

    try {
      const data = await getConversation(accessToken, conversationId)

      setConversation({
        id: data.id,
        title: data.title,
      })

      setMessages(
        data.messages.map((message) => ({
          id: message.id,
          role: message.role === 'user' ? 'user' : 'assistant',
          content: message.content,
        })),
      )

      setQuestion('')
    } catch (error) {
      setHistoryError(
        error instanceof Error
          ? error.message
          : 'Unable to open this conversation.',
      )
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginError('')
    setIsLoggingIn(true)

    try {
      const result = await login(email.trim(), password)
      const currentUser = await getCurrentUser(result.access_token)

      setAccessToken(result.access_token)
      setUser(currentUser)
      setPassword('')

      await loadConversations(result.access_token)
    } catch (error) {
      setLoginError(
        error instanceof Error
          ? error.message
          : 'Unable to sign in. Please try again.',
      )
    } finally {
      setIsLoggingIn(false)
    }
  }

  function handleLogout() {
    setAccessToken(null)
    setUser(null)
    setMessages([])
    setQuestion('')
    setPassword('')
    setEmail('')
    setConversation(null)
    setConversations([])
    setHistoryError('')
    setChatError('')
    setActiveSection('chat')
  }

  async function handleSendMessage() {
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion || !accessToken || isSending) return

    setQuestion('')
    setChatError('')
    setHistoryError('')
    setIsSending(true)

    const userMessageId = Date.now()
    const assistantMessageId = userMessageId + 1

    const userMessage: Message = {
      id: userMessageId,
      role: 'user',
      content: trimmedQuestion,
    }

    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      sources: [],
    }

    setMessages((previous) => [
      ...previous,
      userMessage,
      assistantMessage,
    ])

    try {
      let activeConversation = conversation

      if (!activeConversation) {
        activeConversation = await createConversation(
          accessToken,
          trimmedQuestion.slice(0, 80) || 'New Conversation',
        )

        setConversation(activeConversation)

        // Refresh the sidebar so the new conversation appears.
        await loadConversations(accessToken)
      }

      await streamChat(
        accessToken,
        trimmedQuestion,
        activeConversation.id,
        {
          onToken: (token) => {
            setMessages((previous) =>
              previous.map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      content: message.content + token,
                    }
                  : message,
              ),
            )
          },

          onSources: (sources: ChatSource[]) => {
            setMessages((previous) =>
              previous.map((message) => {
                if (message.id !== assistantMessageId) {
                  return message
                }

                const filenames = sources.map((source) => {
                  const filename =
                    source.filename ??
                    source.document_name ??
                    source.title ??
                    source.source ??
                    source.document_id ??
                    'Source document'

                  return String(filename)
                })

                return {
                  ...message,
                  sources: filenames,
                }
              }),
            )
          },
        },
      )
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Failed to get an AI response.'

      setChatError(errorMessage)

      setMessages((previous) =>
        previous.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content:
                  message.content || 'Unable to generate a response.',
              }
            : message,
        ),
      )
    } finally {
      setIsSending(false)
    }
  }

  function handleNewChat() {
    if (isSending) return

    setMessages([])
    setQuestion('')
    setConversation(null)
    setChatError('')
    setHistoryError('')
    setActiveSection('chat')
  }

  if (!accessToken) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="brand login-brand">
            <div className="brand-icon">R</div>
            <div>
              <h2>Retrieval AI</h2>
              <span>Enterprise Assistant</span>
            </div>
          </div>

          <div className="login-heading">
            <div className="eyebrow">WELCOME BACK</div>
            <h1>Sign in to your workspace</h1>
            <p>Access your organization's knowledge assistant.</p>
          </div>

          <form className="login-form" onSubmit={handleLogin}>
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />

            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />

            {loginError && (
              <div className="login-error" role="alert">
                {loginError}
              </div>
            )}

            <button
              className="login-submit"
              type="submit"
              disabled={isLoggingIn}
            >
              {isLoggingIn ? 'Signing in...' : 'Sign in'}
              {!isLoggingIn && <span>→</span>}
            </button>
          </form>

          <div className="login-footer">
            Secure access to your enterprise knowledge
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">R</div>
          <div>
            <h2>Retrieval AI</h2>
            <span>Enterprise Assistant</span>
          </div>
        </div>

        <button
          className="new-chat-button"
          onClick={handleNewChat}
          disabled={isSending}
        >
          <span>＋</span> New conversation
        </button>

        <div className="sidebar-label">WORKSPACE</div>

        <button
          className={`nav-item ${activeSection === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveSection('chat')}
        >
          <span>▤</span> AI Assistant
        </button>

        <button
          className={`nav-item ${activeSection === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveSection('documents')}
        >
          <span>▧</span> Documents
        </button>

        <div className="sidebar-label conversation-history-heading">
          RECENT CONVERSATIONS
        </div>

        <div className="conversation-history">
          {isLoadingHistory && (
            <div className="history-status">
              Loading conversations...
            </div>
          )}

          {historyError && (
            <div className="history-error" role="alert">
              {historyError}
            </div>
          )}

          {!isLoadingHistory &&
            !historyError &&
            conversations.length === 0 && (
              <div className="history-status">
                No saved conversations yet.
              </div>
            )}

          {conversations.map((item) => (
            <button
              key={item.id}
              className={`conversation-item ${
                conversation?.id === item.id ? 'selected' : ''
              }`}
              onClick={() => void handleSelectConversation(item.id)}
              disabled={isSending}
              title={item.title}
            >
              <span className="conversation-item-icon">▤</span>
              <span className="conversation-item-title">
                {item.title}
              </span>
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="status-indicator" />
          <div className="sidebar-user">
            <strong>
              {user?.email ?? user?.username ?? 'Signed in'}
            </strong>
            <span>{user?.role ?? 'Authenticated user'}</span>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace</span>
            <span className="breadcrumb-separator"> / </span>
            <strong>
              {activeSection === 'chat' ? 'AI Assistant' : 'Documents'}
            </strong>
          </div>

          <button className="logout-button" onClick={handleLogout}>
            Sign out
          </button>
        </header>

        {activeSection === 'chat' ? (
          <section className="chat-page">
            {messages.length === 0 ? (
              <div className="welcome-area">
                <div className="welcome-icon">✳</div>
                <div className="eyebrow">YOUR KNOWLEDGE, CONNECTED</div>

                <h1>
                  Ask your documents.
                  <br />
                  <span>Get grounded answers.</span>
                </h1>

                <p className="welcome-description">
                  Ask questions about your organization's knowledge.
                  Your AI assistant will use relevant document context
                  to help answer your questions.
                </p>

                <div className="suggestion-grid">
                  <button
                    className="suggestion-card"
                    onClick={() =>
                      setQuestion(
                        'What information is available in my documents?',
                      )
                    }
                  >
                    <span className="suggestion-icon purple">⌕</span>
                    <strong>Explore your knowledge</strong>
                    <span>
                      Find relevant information in your documents.
                    </span>
                  </button>

                  <button
                    className="suggestion-card"
                    onClick={() =>
                      setQuestion(
                        'Summarize the key points in my documents.',
                      )
                    }
                  >
                    <span className="suggestion-icon blue">≡</span>
                    <strong>Summarize documents</strong>
                    <span>
                      Get a concise overview of key information.
                    </span>
                  </button>

                  <button
                    className="suggestion-card"
                    onClick={() =>
                      setQuestion(
                        'Explain the main concepts in my documents.',
                      )
                    }
                  >
                    <span className="suggestion-icon green">◇</span>
                    <strong>Understand a topic</strong>
                    <span>
                      Get explanations grounded in your knowledge base.
                    </span>
                  </button>

                  <button
                    className="suggestion-card"
                    onClick={() =>
                      setQuestion(
                        'Which documents are relevant to my question?',
                      )
                    }
                  >
                    <span className="suggestion-icon orange">↗</span>
                    <strong>Find sources</strong>
                    <span>
                      Discover documents relevant to a question.
                    </span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="messages-area">
                {messages.map((message) => (
                  <div
                    className={`message-row ${message.role}`}
                    key={message.id}
                  >
                    <div className="message-avatar">
                      {message.role === 'user' ? 'U' : 'R'}
                    </div>

                    <div className="message-content">
                      <div className="message-author">
                        {message.role === 'user' ? 'You' : 'Retrieval AI'}
                      </div>

                      <div className="message-text">
                        {message.content ||
                          (isSending && message.role === 'assistant'
                            ? 'Thinking...'
                            : '')}
                      </div>

                      {message.sources && message.sources.length > 0 && (
                        <div className="source-list">
                          <strong>Sources</strong>
                          {message.sources.map((source, index) => (
                            <div
                              className="source-item"
                              key={`${source}-${index}`}
                            >
                              ▤ {source}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {chatError && (
              <div
                className="login-error"
                role="alert"
                style={{
                  width: 'min(790px, calc(100% - 48px))',
                  margin: '0 auto 12px',
                }}
              >
                {chatError}
              </div>
            )}

            <div className="composer-wrapper">
              <form
                className="composer"
                onSubmit={(event) => {
                  event.preventDefault()
                  void handleSendMessage()
                }}
              >
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      event.key === 'Enter' &&
                      !event.shiftKey &&
                      !isSending
                    ) {
                      event.preventDefault()
                      void handleSendMessage()
                    }
                  }}
                  placeholder="Ask a question about your documents..."
                  rows={2}
                  aria-label="Your question"
                  disabled={isSending}
                />

                <div className="composer-footer">
                  <span>
                    AI responses should be verified against source documents.
                  </span>

                  <button
                    className="send-button"
                    type="submit"
                    disabled={!question.trim() || isSending}
                  >
                    {isSending ? 'Thinking...' : 'Send'}
                    {!isSending && <span>↑</span>}
                  </button>
                </div>
              </form>

              <div className="composer-disclaimer">
                Powered by retrieval-augmented generation
              </div>
            </div>
          </section>
        ) : (
          <section className="documents-page">
            <div className="page-heading">
              <div>
                <div className="eyebrow">KNOWLEDGE BASE</div>
                <h1>Documents</h1>
                <p>
                  Manage the documents available to your AI assistant.
                </p>
              </div>
            </div>

            <div className="documents-placeholder">
              <div className="welcome-icon">▧</div>
              <h2>Document management</h2>
              <p>
                This workspace will connect to your document upload,
                processing, and indexing APIs.
              </p>
              <span className="coming-soon">Integration pending</span>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
