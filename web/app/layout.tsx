import './globals.css'
import type { Metadata } from 'next'
import { AuthProvider } from '../lib/AuthContext'

export const metadata: Metadata = {
  title: 'Sentinel AI — Real-Time Financial Fraud Intelligence',
  description: 'Enterprise Adaptive Credit Card Fraud Intelligence Platform powered by Apache Kafka, Spark, and Behavioral Analytics',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-canvas text-ink antialiased font-sans">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
