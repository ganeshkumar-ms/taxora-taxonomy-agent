import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : (import.meta.env.DEV ? 'http://localhost:8000' : '')

async function classifyViaPresignedS3(file, text, conversationHistory = []) {
  const contentType = file.type || 'application/octet-stream'
  const urlRes = await axios.post(`${BASE}/api/upload-url`, {
    filename: file.name,
    content_type: contentType,
  })
  const { upload_url, s3_key } = urlRes.data
  await axios.put(upload_url, file, {
    headers: { 'Content-Type': contentType },
  })
  const classifyRes = await axios.post(`${BASE}/api/classify`, {
    s3_key,
    filename: file.name,
    text: text || '',
    conversation_history: conversationHistory,
  })
  return classifyRes.data
}

async function classifyViaMultipart(file, text, conversationHistory = []) {
  const form = new FormData()
  if (file) form.append('file', file)
  if (text) form.append('text', text)
  form.append('conversation_history', JSON.stringify(conversationHistory))
  const res = await axios.post(`${BASE}/api/classify`, form)
  return res.data
}

export async function classifyContent(file, text, conversationHistory = []) {
  if (file) {
    const isZipOrLarge =
      file.size > 1.8 * 1024 * 1024 ||
      file.name.toLowerCase().endsWith('.zip')

    if (isZipOrLarge) {
      try {
        return await classifyViaPresignedS3(file, text, conversationHistory)
      } catch {
        return await classifyViaMultipart(file, text, conversationHistory)
      }
    }

    try {
      return await classifyViaMultipart(file, text, conversationHistory)
    } catch (err) {
      // Fallback to S3 presigned upload if direct multipart hits a payload or network limit
      try {
        return await classifyViaPresignedS3(file, text, conversationHistory)
      } catch {
        throw err
      }
    }
  }

  return await classifyViaMultipart(null, text, conversationHistory)
}

export async function getTaxonomy() {
  const res = await axios.get(`${BASE}/api/taxonomy`)
  return res.data
}

export async function submitFeedback(action, editedPath = null) {
  const res = await axios.post(`${BASE}/api/feedback`, { action, edited_path: editedPath })
  return res.data
}

// Builds the info the document viewer needs from a file / document_metadata object.
export function toViewerDoc(meta) {
  if (!meta) return null
  const abs = u => (u ? (u.startsWith('http') ? u : `${BASE}${u}`) : null)
  return {
    name: meta.filename || meta.name || 'Document',
    viewUrl: abs(meta.view_url),
    downloadUrl: abs(meta.url),
    preview: meta.preview || '',
    rawMeta: meta
  }
}
