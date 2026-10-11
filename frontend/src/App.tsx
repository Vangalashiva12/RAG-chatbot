
import { useEffect, useState, type FormEvent, type ChangeEvent } from 'react'
import './App.css'
import {
  login,
  getCurrentUser,
  createConversation,
  streamChat,
  getConversations,
  getConversation,
  getDocuments,
  uploadDocument,
  getDocument,
  processDocument,
  embedDocument,
  deleteDocument,
  type User,
  type ChatSource,
  type Conversation,
  type Document as ApiDocument,
  type DocumentDetail,
} from './services/api'

type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

const MAX_FILE_SIZE = 10 * 1024 * 1024
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.csv', '.md', '.pptx']

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function getStatusClass(status: string): string {
  const normalized = status.toLowerCase()

  if (normalized === 'failed') return 'document-status-failed'
  if (normalized === 'uploaded') return 'document-status-uploaded'
  if (normalized === 'processing') return 'document-status-processing'
  if (normalized === 'chunked') return 'document-status-chunked'
  if (normalized === 'completed' || normalized === 'ready' || normalized === 'processed') {
    return 'document-status-ready'
  }

  return 'document-status-default'
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

  // Document management state
  const [documents, setDocuments] = useState<ApiDocument[]>([])
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false)
  const [documentError, setDocumentError] = useState('')
  const [documentNotice, setDocumentNotice] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [activeDocumentAction, setActiveDocumentAction] = useState<number | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<DocumentDetail | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)

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

  async function loadDocuments(token: string) {
    setIsLoadingDocuments(true)
    setDocumentError('')

    try {
      const data = await getDocuments(token)
      setDocuments(data)
    } catch (error) {
      setDocumentError(
        error instanceof Error
          ? error.message
          : 'Unable to load documents.',
      )
    } finally {
      setIsLoadingDocuments(false)
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
    setDocuments([])
    setDocumentError('')
    setDocumentNotice('')
    setSelectedDocument(null)
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
      let activeConversation: Conversation | null = conversation

      if (!activeConversation) {
        const created = await createConversation(
          accessToken,
          trimmedQuestion.slice(0, 80) || 'New Conversation',
        )

        activeConversation = created as Conversation
        setConversation(activeConversation)
        await loadConversations(accessToken)
      }

      // Keep TypeScript aware that the ID exists before streaming.
      const conversationId = activeConversation?.id

      if (conversationId == null) {
        throw new Error('Unable to create or select a conversation.')
      }

      await streamChat(
        accessToken,
        trimmedQuestion,
        conversationId,
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
                if (message.id !== assistantMessageId) return message

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

          onDone: () => {
            // The finally block resets the sending state.
          },

          onError: (error: string) => {
            setChatError(error)
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

  async function handleDocumentSection() {
    setActiveSection('documents')
    setDocumentNotice('')
    setDocumentError('')

    if (accessToken) {
      await loadDocuments(accessToken)
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget
    const file = input.files?.[0]

    if (!file || !accessToken) return

    setDocumentError('')
    setDocumentNotice('')

    const extension = `.${file.name.split('.').pop()?.toLowerCase()}`

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setDocumentError(
        'Unsupported file type. Upload PDF, DOCX, TXT, CSV, MD, or PPTX.',
      )
      input.value = ''
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      setDocumentError('File size exceeds the 10 MB limit.')
      input.value = ''
      return
    }

    if (file.size === 0) {
      setDocumentError('The selected file is empty.')
      input.value = ''
      return
    }

    setIsUploading(true)

    try {
      const result = await uploadDocument(accessToken, file)

      setDocumentNotice(
        `${result.filename} uploaded successfully. Document ingestion may continue in the background.`,
      )

      await loadDocuments(accessToken)
    } catch (error) {
      setDocumentError(
        error instanceof Error
          ? error.message
          : 'Document upload failed.',
      )
    } finally {
      setIsUploading(false)
      input.value = ''
    }
  }

  async function handleRefreshDocuments() {
    if (!accessToken) return

    setDocumentNotice('')
    await loadDocuments(accessToken)
  }

  async function handleViewDocument(documentId: number) {
    if (!accessToken) return

    setDocumentError('')
    setDocumentNotice('')
    setIsLoadingDetails(true)
    setSelectedDocument(null)

    try {
      const detail = await getDocument(accessToken, documentId)
      setSelectedDocument(detail)
    } catch (error) {
      setDocumentError(
        error instanceof Error
          ? error.message
          : 'Unable to load document details.',
      )
    } finally {
      setIsLoadingDetails(false)
    }
  }

  async function handleProcessDocument(document: ApiDocument) {
    if (!accessToken) return

    setActiveDocumentAction(document.id)
    setDocumentError('')
    setDocumentNotice('')

    try {
      const result = await processDocument(accessToken, document.id)

      setDocumentNotice(
        `${result.filename}: processing complete. ${result.chunks_created} chunks created.`,
      )

      await loadDocuments(accessToken)

      if (selectedDocument?.id === document.id) {
        const detail = await getDocument(accessToken, document.id)
        setSelectedDocument(detail)
      }
    } catch (error) {
      setDocumentError(
        error instanceof Error
          ? error.message
          : 'Document processing failed.',
      )
      await loadDocuments(accessToken)
    } finally {
      setActiveDocumentAction(null)
    }
  }

  async function handleEmbedDocument(document: ApiDocument) {
    if (!accessToken) return

    setActiveDocumentAction(document.id)
    setDocumentError('')
    setDocumentNotice('')

    try {
      const result = await embedDocument(accessToken, document.id)

      setDocumentNotice(
        `Embeddings generated for document #${result.document_id}: ${result.chunks_embedded} chunks, ${result.embedding_dimension} dimensions.`,
      )

      await loadDocuments(accessToken)

      if (selectedDocument?.id === document.id) {
        const detail = await getDocument(accessToken, document.id)
        setSelectedDocument(detail)
      }
    } catch (error) {
      setDocumentError(
        error instanceof Error
          ? error.message
          : 'Embedding generation failed.',
      )
    } finally {
      setActiveDocumentAction(null)
    }
  }

  async function handleDeleteDocument(document: ApiDocument) {
    if (!accessToken) return

    const confirmed = window.confirm(
      `Delete "${document.filename}"? This will permanently remove the document and its chunks.`,
    )

    if (!confirmed) return

    setActiveDocumentAction(document.id)
    setDocumentError('')
    setDocumentNotice('')

    try {
      await deleteDocument(accessToken, document.id)

      setDocumentNotice(`"${document.filename}" was deleted.`)

      if (selectedDocument?.id === document.id) {
        setSelectedDocument(null)
      }

      await loadDocuments(accessToken)
    } catch (error) {
      setDocumentError(
        error instanceof Error
          ? error.message
          : 'Document deletion failed.',
      )
    } finally {
      setActiveDocumentAction(null)
    }
  }

  useEffect(() => {
    if (accessToken && activeSection === 'documents') {
      void loadDocuments(accessToken)
    }
    // Load documents when the user opens the Documents section.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, activeSection])

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
          onClick={() => void handleDocumentSection()}
        >
          <span>▧</span> Documents
        </button>

        <div className="sidebar-label conversation-history-heading">
          RECENT CONVERSATIONS
        </div>

        <div className="conversation-history">
          {isLoadingHistory && (
            <div className="history-status">Loading conversations...</div>
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
              <span className="conversation-item-title">{item.title}</span>
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
                    <span>Find relevant information in your documents.</span>
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
                    <span>Get a concise overview of key information.</span>
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
                    <span>Get explanations grounded in your knowledge base.</span>
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
                    <span>Discover documents relevant to a question.</span>
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
          <section className="documents-page" style={{ padding: '32px', overflowY: 'auto' }}>
            <div
              className="page-heading"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '16px',
                flexWrap: 'wrap',
              }}
            >
              <div>
                <div className="eyebrow">KNOWLEDGE BASE</div>
                <h1>Documents</h1>
                <p>Upload and manage the documents used by your AI assistant.</p>
              </div>

              <button
                type="button"
                className="send-button"
                onClick={() => void handleRefreshDocuments()}
                disabled={isLoadingDocuments || isUploading}
              >
                {isLoadingDocuments ? 'Refreshing...' : '↻ Refresh'}
              </button>
            </div>

            <div
              style={{
                marginTop: '24px',
                padding: '24px',
                border: '1px dashed #c9c5e9',
                borderRadius: '14px',
                background: '#faf9ff',
              }}
            >
              <h2 style={{ marginTop: 0 }}>Upload a document</h2>
              <p>
                Supported formats: PDF, DOCX, TXT, CSV, MD, PPTX. Maximum size: 10 MB.
              </p>

              <label
                htmlFor="document-upload"
                className="login-submit"
                style={{
                  display: 'inline-flex',
                  width: 'auto',
                  cursor: isUploading ? 'wait' : 'pointer',
                  opacity: isUploading ? 0.6 : 1,
                }}
              >
                {isUploading ? 'Uploading...' : '＋ Choose file'}
              </label>

              <input
                id="document-upload"
                type="file"
                accept=".pdf,.docx,.txt,.csv,.md,.pptx"
                onChange={(event) => void handleUpload(event)}
                disabled={isUploading}
                style={{
                  position: 'absolute',
                  width: '1px',
                  height: '1px',
                  padding: 0,
                  margin: '-1px',
                  overflow: 'hidden',
                  clip: 'rect(0, 0, 0, 0)',
                  whiteSpace: 'nowrap',
                  border: 0,
                }}
              />

              {isUploading && (
                <p role="status">Uploading your document...</p>
              )}
            </div>

            {documentError && (
              <div className="login-error" role="alert" style={{ marginTop: '16px' }}>
                {documentError}
              </div>
            )}

            {documentNotice && (
              <div
                role="status"
                style={{
                  marginTop: '16px',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  background: '#edf8f0',
                  color: '#246b3c',
                  overflowWrap: 'anywhere',
                }}
              >
                {documentNotice}
              </div>
            )}

            <div style={{ marginTop: '32px' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '12px',
                  marginBottom: '16px',
                }}
              >
                <h2 style={{ margin: 0 }}>Uploaded documents</h2>
                <span>{documents.length} total</span>
              </div>

              {isLoadingDocuments && documents.length === 0 && (
                <p role="status">Loading documents...</p>
              )}

              {!isLoadingDocuments && documents.length === 0 && !documentError && (
                <div
                  style={{
                    padding: '32px 20px',
                    textAlign: 'center',
                    border: '1px solid #e8e7ef',
                    borderRadius: '12px',
                  }}
                >
                  <div className="welcome-icon">▧</div>
                  <h3>No documents yet</h3>
                  <p>Upload your first document to start building your knowledge base.</p>
                </div>
              )}

              {documents.length > 0 && (
                <div style={{ overflowX: 'auto' }}>
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      textAlign: 'left',
                      minWidth: '720px',
                    }}
                  >
                    <thead>
                      <tr>
                        <th style={tableHeaderStyle}>Document</th>
                        <th style={tableHeaderStyle}>Size</th>
                        <th style={tableHeaderStyle}>Status</th>
                        <th style={tableHeaderStyle}>Actions</th>
                      </tr>
                    </thead>

                    <tbody>
                      {documents.map((document) => {
                        const isBusy = activeDocumentAction === document.id
                        const normalizedStatus = document.status.toUpperCase()

                        return (
                          <tr key={document.id}>
                            <td style={tableCellStyle}>
                              <button
                                type="button"
                                onClick={() => void handleViewDocument(document.id)}
                                style={{
                                  padding: 0,
                                  border: 0,
                                  background: 'transparent',
                                  color: '#6254e8',
                                  cursor: 'pointer',
                                  textAlign: 'left',
                                  fontWeight: 600,
                                }}
                              >
                                {document.filename}
                              </button>
                              <div style={{ fontSize: '12px', color: '#777', marginTop: '4px' }}>
                                {document.file_type.toUpperCase()} · ID {document.id}
                              </div>
                            </td>

                            <td style={tableCellStyle}>
                              {formatFileSize(document.file_size)}
                            </td>

                            <td style={tableCellStyle}>
                              <span className={getStatusClass(document.status)}>
                                {document.status}
                              </span>
                            </td>

                            <td style={tableCellStyle}>
                              <div
                                style={{
                                  display: 'flex',
                                  flexWrap: 'wrap',
                                  gap: '6px',
                                }}
                              >
                                <button
                                  type="button"
                                  onClick={() => void handleViewDocument(document.id)}
                                  disabled={isBusy || isLoadingDetails}
                                  style={smallButtonStyle}
                                >
                                  Details
                                </button>

                                {normalizedStatus !== 'CHUNKED' &&
                                  normalizedStatus !== 'PROCESSING' && (
                                    <button
                                      type="button"
                                      onClick={() => void handleProcessDocument(document)}
                                      disabled={isBusy}
                                      style={smallButtonStyle}
                                    >
                                      {isBusy ? 'Working...' : 'Process'}
                                    </button>
                                  )}

                                {normalizedStatus === 'CHUNKED' && (
                                  <button
                                    type="button"
                                    onClick={() => void handleEmbedDocument(document)}
                                    disabled={isBusy}
                                    style={smallButtonStyle}
                                  >
                                    {isBusy ? 'Working...' : 'Generate embeddings'}
                                  </button>
                                )}

                                <button
                                  type="button"
                                  onClick={() => void handleDeleteDocument(document)}
                                  disabled={isBusy}
                                  style={{
                                    ...smallButtonStyle,
                                    color: '#a52e36',
                                  }}
                                >
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {isLoadingDetails && (
              <p role="status" style={{ marginTop: '24px' }}>
                Loading document details...
              </p>
            )}

            {selectedDocument && (
              <div
                style={{
                  marginTop: '28px',
                  padding: '24px',
                  border: '1px solid #e8e7ef',
                  borderRadius: '12px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: '16px',
                    alignItems: 'flex-start',
                  }}
                >
                  <div>
                    <div className="eyebrow">DOCUMENT DETAILS</div>
                    <h2 style={{ overflowWrap: 'anywhere' }}>
                      {selectedDocument.filename}
                    </h2>
                  </div>

                  <button
                    type="button"
                    onClick={() => setSelectedDocument(null)}
                    style={smallButtonStyle}
                  >
                    Close
                  </button>
                </div>

                <p><strong>Document ID:</strong> {selectedDocument.id}</p>
                <p><strong>Status:</strong> {selectedDocument.status}</p>
                <p><strong>File size:</strong> {formatFileSize(selectedDocument.file_size)}</p>
                <p><strong>Chunks:</strong> {selectedDocument.chunk_count}</p>
                <p>
                  <strong>Extracted characters:</strong>{' '}
                  {selectedDocument.extracted_text?.length ?? 0}
                </p>

                {selectedDocument.extracted_text && (
                  <details style={{ marginTop: '16px' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
                      Preview extracted text
                    </summary>
                    <pre
                      style={{
                        maxHeight: '360px',
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                        overflowWrap: 'anywhere',
                        padding: '16px',
                        background: '#f7f7fa',
                        borderRadius: '8px',
                        fontSize: '13px',
                        lineHeight: 1.6,
                      }}
                    >
                      {selectedDocument.extracted_text}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

const tableHeaderStyle = {
  padding: '14px 12px',
  borderBottom: '1px solid #e8e7ef',
  color: '#686b7c',
  fontSize: '12px',
  textTransform: 'uppercase' as const,
  letterSpacing: '0.04em',
}

const tableCellStyle = {
  padding: '16px 12px',
  borderBottom: '1px solid #eeeef3',
  verticalAlign: 'top' as const,
}

const smallButtonStyle = {
  padding: '7px 10px',
  border: '1px solid #dedce9',
  borderRadius: '7px',
  background: '#fff',
  color: '#514b70',
  cursor: 'pointer',
  fontSize: '12px',
}

export default App
