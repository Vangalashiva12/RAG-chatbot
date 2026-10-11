
const API_BASE_URL = 'http://localhost:8000'

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface User {
  id?: number
  email?: string
  username?: string
  role?: string
  [key: string]: unknown
}

async function readError(response: Response): Promise<string> {
  const body = await response.text()

  try {
    const parsed = JSON.parse(body)
    return parsed.detail ?? `Request failed (${response.status})`
  } catch {
    return body || `Request failed (${response.status})`
  }
}

export async function login(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const formData = new URLSearchParams()
  formData.set('username', email)
  formData.set('password', password)

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  const data = (await response.json()) as LoginResponse

  if (!data.access_token) {
    throw new Error('Login response did not contain an access token.')
  }

  return data
}

export async function getCurrentUser(
  accessToken: string,
): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return (await response.json()) as User
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
    throw new Error(await readError(response))
  }

  return response
}


export interface ChatSource {
  [key: string]: unknown
}

export interface StreamCallbacks {
  onToken: (token: string) => void
  onSources: (sources: ChatSource[]) => void
  onDone?: () => void
}

export async function streamChat(
  accessToken: string,
  question: string,
  conversationId: number,
  callbacks: StreamCallbacks,
  topK = 5,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
      top_k: topK,
    }),
    signal,
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  if (!response.body) {
    throw new Error('The server did not return a readable response stream.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      buffer = buffer.replace(/\r\n/g, '\n')

      let boundary = buffer.indexOf('\n\n')

      while (boundary !== -1) {
        const eventBlock = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)

        for (const line of eventBlock.split('\n')) {
          if (!line.startsWith('data:')) continue

          const payload = line.slice(5).trim()
          if (!payload) continue

          let event: {
            type?: string
            content?: string
            sources?: ChatSource[]
            message?: string
            detail?: string
          }

          try {
            event = JSON.parse(payload)
          } catch {
            throw new Error('Received an invalid streaming event from the server.')
          }

          if (event.type === 'token' && event.content) {
            callbacks.onToken(event.content)
          } else if (event.type === 'sources') {
            callbacks.onSources(event.sources ?? [])
          } else if (event.type === 'done') {
            callbacks.onDone?.()
          } else if (event.type === 'error') {
            throw new Error(
              event.message ?? event.detail ?? 'The server reported a chat error.',
            )
          }
        }

        boundary = buffer.indexOf('\n\n')
      }
    }
  } finally {
    reader.releaseLock()
  }
}


export interface Conversation {
  id: number
  title: string
}

export async function createConversation(
  accessToken: string,
  title = 'New Conversation',
): Promise<Conversation> {
  const response = await authenticatedFetch(
    '/conversations/',
    accessToken,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    },
  )

  return (await response.json()) as Conversation
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

export async function getConversations(
  accessToken: string,
): Promise<Conversation[]> {
  const response = await authenticatedFetch(
    '/conversations/',
    accessToken,
  )

  return (await response.json()) as Conversation[]
}

export async function getConversation(
  accessToken: string,
  conversationId: number,
): Promise<ConversationDetail> {
  const response = await authenticatedFetch(
    `/conversations/${conversationId}`,
    accessToken,
  )

  return (await response.json()) as ConversationDetail
}
