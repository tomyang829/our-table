import { useCallback, useMemo, useRef, useState } from 'react'

interface BrowserSpeechRecognitionAlternative {
  transcript: string
}

interface BrowserSpeechRecognitionResult {
  isFinal: boolean
  0: BrowserSpeechRecognitionAlternative
}

interface BrowserSpeechRecognitionResultList {
  length: number
  [index: number]: BrowserSpeechRecognitionResult
}

interface BrowserSpeechRecognitionEvent {
  resultIndex: number
  results: BrowserSpeechRecognitionResultList
}

interface BrowserSpeechRecognitionErrorEvent {
  error: string
}

interface BrowserSpeechRecognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition

declare global {
  interface Window {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor
  }
}

interface StartDictationOptions {
  onTranscript: (chunk: string) => void
  lang?: string
}

export function useBrowserDictation() {
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)
  const onTranscriptRef = useRef<((chunk: string) => void) | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const recognitionConstructor = useMemo(
    () =>
      typeof window !== 'undefined'
        ? (window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null)
        : null,
    [],
  )
  const isSupported = recognitionConstructor !== null

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const start = useCallback(
    ({ onTranscript, lang = 'en-US' }: StartDictationOptions) => {
      if (!recognitionConstructor) {
        setError('Speech dictation is not supported in this browser.')
        return
      }

      setError(null)
      onTranscriptRef.current = onTranscript

      recognitionRef.current?.stop()
      const recognition = new recognitionConstructor()
      recognition.lang = lang
      recognition.continuous = true
      recognition.interimResults = true

      recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const result = event.results[i]
          if (!result.isFinal) continue
          const transcript = result[0]?.transcript?.trim()
          if (!transcript) continue
          onTranscriptRef.current?.(transcript)
        }
      }

      recognition.onerror = (event) => {
        setError(`Speech dictation failed: ${event.error}`)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognition
      recognition.start()
      setIsListening(true)
    },
    [recognitionConstructor],
  )

  return { isSupported, isListening, error, start, stop, clearError }
}
