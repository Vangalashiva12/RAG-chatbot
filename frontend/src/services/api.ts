
const API_BASE_URL = 'http://localhost:8000'

export interface User {
  id?: number
  email?: string
  username?: string
  role?: string
  [key: string]: unknown
}

export interface Conversation {
  id: number
  title: string
}

export interface ConversationMessage {
  id: number
  role: string
  content: string
}

export interface ConversationDetail {
  id: number
  title: string
  messages: ConversationMessage[]
}

export interface ChatSource {
  [key: string]: unknown
}

export interface Document {
  id: number
  filename: string
  file_type: string
  file_size: number
  uploaded_by: number
  status: string
}

export interface DocumentDetail extends Document {
  extracted_text: string | null
  chunk_count: number
}

export interface DocumentUploadResponse {
  message: string
  document_id: number
  filename: string
  file_type: string
  file_size: number
  status: string
}

export interface DocumentProcessResponse {
  message: string
  document_id: number
  filename: string
  status: string
  characters_extracted: number
  chunks_created: number
}

export interface DocumentEmbedResponse {
  message: string
  document_id: number
  chunks_embedded: number
  embedding_dimension: number
}

export async function login(email: string, password: string) {
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

export async function getCurrentUser(
  accessToken: string,
): Promise<User> {
  const response = await authenticatedFetch('/auth/me', accessToken)
  return response.json()
}

export async function authenticatedFetch(
  path: string,
  accessToken: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${accessToken}`)

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(
      error.detail || `Request failed (${response.status})`,
    )
  }

  return response
}

export async function streamChat(
  accessToken: string,
  question: string,
  conversationId: number,
  callbacks: {
    onToken: (content: string) => void
    onSources: (sources: ChatSource[]) => void
    onDone: () => void
    onError: (error: string) => void
  },
  topK = 5,
  signal?: AbortSignal,
): Promise<void> {
  const response = await authenticatedFetch('/chat/stream', accessToken, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
      top_k: topK,
    }),
    signal,
  })

  if (!response.body) {
    throw new Error('Streaming response body is unavailable')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() || ''

      for (const event of events) {
        const dataLine = event
          .split('\n')
          .find((line) => line.startsWith('data:'))

        if (!dataLine) continue

        try {
          const data = JSON.parse(dataLine.slice(5).trim())

          if (data.type === 'token') {
            callbacks.onToken(data.content || '')
          } else if (data.type === 'sources') {
            callbacks.onSources(data.sources || [])
          } else if (data.type === 'done') {
            callbacks.onDone()
          } else if (data.type === 'error') {
            callbacks.onError(data.message || 'Streaming failed')
          }
        } catch {
          // Ignore malformed SSE event data.
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export async function createConversation(
  accessToken: string,
  title = 'New Conversation',
) {
  const response = await authenticatedFetch('/conversations/', accessToken, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })

  return response.json()
}

export async function getConversations(
  accessToken: string,
): Promise<Conversation[]> {
  const response = await authenticatedFetch(
    '/conversations/',
    accessToken,
  )
  return response.json()
}

export async function getConversation(
  accessToken: string,
  conversationId: number,
): Promise<ConversationDetail> {
  const response = await authenticatedFetch(
    `/conversations/${conversationId}`,
    accessToken,
  )
  return response.json()
}

// ============================================================
// Document Management API
// ============================================================

export async function getDocuments(
  accessToken: string,
): Promise<Document[]> {
  const response = await authenticatedFetch('/documents/', accessToken)
  return response.json()
}

export async function uploadDocument(
  accessToken: string,
  file: File,
): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  // Do not manually set Content-Type for FormData.
  // The browser must generate the multipart boundary.
  const response = await authenticatedFetch(
    '/documents/upload',
    accessToken,
    {
      method: 'POST',
      body: formData,
    },
  )

  return response.json()
}

export async function getDocument(
  accessToken: string,
  documentId: number,
): Promise<DocumentDetail> {
  const response = await authenticatedFetch(
    `/documents/${documentId}`,
    accessToken,
  )
  return response.json()
}

export async function processDocument(
  accessToken: string,
  documentId: number,
): Promise<DocumentProcessResponse> {
  const response = await authenticatedFetch(
    `/documents/${documentId}/process`,
    accessToken,
    { method: 'POST' },
  )
  return response.json()
}

export async function embedDocument(
  accessToken: string,
  documentId: number,
): Promise<DocumentEmbedResponse> {
  const response = await authenticatedFetch(
    `/documents/${documentId}/embed`,
    accessToken,
    { method: 'POST' },
  )
  return response.json()
}

export async function deleteDocument(
  accessToken: string,
  documentId: number,
): Promise<void> {
  await authenticatedFetch(
    `/documents/${documentId}`,
    accessToken,
    { method: 'DELETE' },
  )
}
