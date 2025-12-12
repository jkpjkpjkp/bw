'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

const API_BASE = 'http://localhost:8080'

async function fetchPersons() {
    const res = await fetch(`${API_BASE}/api/persons`)
    return res.json()
}

async function fetchBook(personIndex) {
    const res = await fetch(`${API_BASE}/api/book/${personIndex}`)
    return res.json()
}

function Card({ person, desiredAge, onSwipe }) {
    const [dragState, setDragState] = useState({ isDragging: false, startX: 0, currentX: 0 })

    const year = person.birth_year + desiredAge
    const context = person.company || person.country || person.field || ''

    const handleMouseDown = (e) => {
        setDragState({ isDragging: true, startX: e.clientX, currentX: 0 })
    }

    const handleMouseMove = useCallback((e) => {
        if (!dragState.isDragging) return
        const deltaX = e.clientX - dragState.startX
        setDragState(prev => ({ ...prev, currentX: deltaX }))
    }, [dragState.isDragging, dragState.startX])

    const handleMouseUp = useCallback(() => {
        if (!dragState.isDragging) return
        const threshold = 100
        if (dragState.currentX > threshold) {
            onSwipe('right')
        } else if (dragState.currentX < -threshold) {
            onSwipe('left')
        }
        setDragState({ isDragging: false, startX: 0, currentX: 0 })
    }, [dragState, onSwipe])

    useEffect(() => {
        if (dragState.isDragging) {
            window.addEventListener('mousemove', handleMouseMove)
            window.addEventListener('mouseup', handleMouseUp)
            return () => {
                window.removeEventListener('mousemove', handleMouseMove)
                window.removeEventListener('mouseup', handleMouseUp)
            }
        }
    }, [dragState.isDragging, handleMouseMove, handleMouseUp])

    const handleTouchStart = (e) => {
        const touch = e.touches[0]
        setDragState({ isDragging: true, startX: touch.clientX, currentX: 0 })
    }

    const handleTouchMove = (e) => {
        if (!dragState.isDragging) return
        const touch = e.touches[0]
        const deltaX = touch.clientX - dragState.startX
        setDragState(prev => ({ ...prev, currentX: deltaX }))
    }

    const handleTouchEnd = () => {
        handleMouseUp()
    }

    const rotation = dragState.currentX * 0.1
    const opacity = Math.min(Math.abs(dragState.currentX) / 100, 1)

    return (
        <div
            style={{
                position: 'absolute',
                width: 'calc(100% - 40px)',
                height: 'calc(100% - 40px)',
                background: 'white',
                borderRadius: 15,
                boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                overflow: 'hidden',
                cursor: dragState.isDragging ? 'grabbing' : 'grab',
                userSelect: 'none',
                transform: `translateX(${dragState.currentX}px) rotate(${rotation}deg)`,
            }}
            onMouseDown={handleMouseDown}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
        >
            <div style={{
                width: '100%',
                height: '65%',
                background: 'linear-gradient(45deg, #f093fb, #f5576c)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 120,
                color: 'white',
                position: 'relative',
            }}>
                <span>👤</span>
                <div style={{
                    position: 'absolute',
                    bottom: 0,
                    left: 0,
                    right: 0,
                    background: 'linear-gradient(transparent, rgba(0,0,0,0.7))',
                    padding: 20,
                    color: 'white',
                }}>
                    <div style={{ fontSize: 28, fontWeight: 'bold' }}>{person.first_name}</div>
                    <div style={{ fontSize: 18 }}>{year}</div>
                </div>
            </div>
            <div style={{ padding: '15px 20px' }}>
                <span style={{
                    display: 'inline-block',
                    padding: '4px 12px',
                    background: '#f0f0f0',
                    borderRadius: 20,
                    fontSize: 12,
                    textTransform: 'capitalize',
                }}>{person.category}</span>
                {context && <div style={{ marginTop: 10, fontSize: 13, color: '#888', fontStyle: 'italic' }}>{context}</div>}
                {person.book && <div style={{ marginTop: 10, fontSize: 13, color: '#888', fontStyle: 'italic' }}>📖 {person.book}</div>}
            </div>

            <div style={{
                position: 'absolute',
                top: '50%',
                right: 20,
                transform: 'translateY(-50%)',
                fontSize: 40,
                fontWeight: 'bold',
                color: '#4CAF50',
                border: '4px solid #4CAF50',
                borderRadius: 10,
                padding: '10px 20px',
                opacity: dragState.currentX > 50 ? opacity : 0,
            }}>LIKE</div>
            <div style={{
                position: 'absolute',
                top: '50%',
                left: 20,
                transform: 'translateY(-50%)',
                fontSize: 40,
                fontWeight: 'bold',
                color: '#F44336',
                border: '4px solid #F44336',
                borderRadius: 10,
                padding: '10px 20px',
                opacity: dragState.currentX < -50 ? opacity : 0,
            }}>NOPE</div>
        </div>
    )
}

function Reader({ person, personIndex, desiredAge, onClose, onAddToLibrary }) {
    const [book, setBook] = useState(null)
    const [loading, setLoading] = useState(true)
    const [currentChapter, setCurrentChapter] = useState(0)
    const [currentPage, setCurrentPage] = useState(0)
    const touchStartX = useRef(0)

    useEffect(() => {
        setLoading(true)
        fetchBook(personIndex)
            .then(data => {
                if (data.error) {
                    setBook({
                        title: person.book || "Autobiography",
                        chapters: [{
                            title: "Coming Soon",
                            text: `The autobiography "${person.book || 'their story'}" by ${person.name} is not yet available.`,
                            age_min: 0,
                            age_max: 100
                        }]
                    })
                } else {
                    setBook(data)
                }
                setLoading(false)
            })
            .catch(() => {
                setBook({
                    title: person.book || "Autobiography",
                    chapters: [{
                        title: "Unavailable",
                        text: "This book could not be loaded.",
                        age_min: 0,
                        age_max: 100
                    }]
                })
                setLoading(false)
            })
    }, [personIndex, person])

    useEffect(() => {
        if (!book) return
        let bestChapter = 0
        let bestSpan = Infinity
        book.chapters.forEach((ch, i) => {
            const ageMin = ch.age_min || 0
            const ageMax = ch.age_max || 100
            if (ageMin <= desiredAge && ageMax >= desiredAge) {
                const span = ageMax - ageMin
                if (span < bestSpan) {
                    bestSpan = span
                    bestChapter = i
                }
            }
        })
        setCurrentChapter(bestChapter)
        setCurrentPage(0)
    }, [book, desiredAge])

    if (loading) {
        return (
            <div style={{ position: 'absolute', inset: 0, background: '#faf8f5', display: 'flex', flexDirection: 'column', zIndex: 100 }}>
                <div style={{ padding: '15px 20px', background: '#333', color: 'white', display: 'flex', justifyContent: 'space-between' }}>
                    <h2>Loading...</h2>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', fontSize: 24, cursor: 'pointer' }}>×</button>
                </div>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading book...</div>
            </div>
        )
    }

    const chapter = book.chapters[currentChapter]
    const paragraphs = chapter?.text.split('\n\n').filter(p => p.trim()) || []
    const PARAGRAPHS_PER_PAGE = 2
    const totalPages = Math.ceil(paragraphs.length / PARAGRAPHS_PER_PAGE)
    const pageContent = paragraphs.slice(currentPage * PARAGRAPHS_PER_PAGE, (currentPage + 1) * PARAGRAPHS_PER_PAGE)

    const handleClick = (e) => {
        const rect = e.currentTarget.getBoundingClientRect()
        const x = e.clientX - rect.left
        const width = rect.width

        if (x < width / 2) {
            if (currentPage > 0) {
                setCurrentPage(p => p - 1)
            } else if (currentChapter > 0) {
                setCurrentChapter(c => c - 1)
                setCurrentPage(0)
            }
        } else {
            if (currentPage < totalPages - 1) {
                setCurrentPage(p => p + 1)
            } else if (currentChapter < book.chapters.length - 1) {
                setCurrentChapter(c => c + 1)
                setCurrentPage(0)
            }
        }
    }

    const handleTouchStart = (e) => {
        touchStartX.current = e.touches[0].clientX
    }

    const handleTouchEnd = (e) => {
        const deltaX = e.changedTouches[0].clientX - touchStartX.current
        const threshold = 50
        if (deltaX > threshold) {
            onAddToLibrary(person)
        } else if (deltaX < -threshold) {
            onClose()
        }
    }

    return (
        <div style={{ position: 'absolute', inset: 0, background: '#faf8f5', display: 'flex', flexDirection: 'column', zIndex: 100 }}>
            <div style={{ padding: '15px 20px', background: '#333', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ fontSize: 16 }}>{book.title}</h2>
                <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', fontSize: 24, cursor: 'pointer' }}>×</button>
            </div>

            <div
                style={{ flex: 1, padding: '30px 25px', overflowY: 'auto', fontSize: 16, lineHeight: 1.8, color: '#333' }}
                onClick={handleClick}
                onTouchStart={handleTouchStart}
                onTouchEnd={handleTouchEnd}
            >
                <h3 style={{ fontSize: 20, marginBottom: 20 }}>{chapter.title}</h3>
                {pageContent.map((p, i) => (
                    <p key={i} style={{ marginBottom: '1.2em', textAlign: 'justify' }}>{p}</p>
                ))}
            </div>

            <div style={{ textAlign: 'center', padding: 5, fontSize: 12, color: '#666' }}>
                Chapter {currentChapter + 1}/{book.chapters.length} • Page {currentPage + 1}/{totalPages}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '15px 20px', background: '#f0f0f0', borderTop: '1px solid #ddd' }}>
                <button onClick={onClose} style={{ padding: '10px 20px', border: 'none', background: '#F44336', color: 'white', borderRadius: 5, cursor: 'pointer' }}>
                    ← Dislike
                </button>
                <button onClick={() => onAddToLibrary(person)} style={{ padding: '10px 20px', border: 'none', background: '#4CAF50', color: 'white', borderRadius: 5, cursor: 'pointer' }}>
                    Add to Library →
                </button>
            </div>
        </div>
    )
}

function Library({ isOpen, onClose, items, onSelect }) {
    return (
        <div style={{
            position: 'absolute',
            top: 0,
            right: isOpen ? 0 : -300,
            bottom: 0,
            width: 300,
            background: 'white',
            boxShadow: '-5px 0 20px rgba(0,0,0,0.2)',
            transition: 'right 0.3s ease',
            zIndex: 50,
            display: 'flex',
            flexDirection: 'column',
        }}>
            <div style={{ padding: 20, background: '#2196F3', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3>My Library</h3>
                <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', fontSize: 24, cursor: 'pointer' }}>×</button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
                {items.length === 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#999' }}>
                        <span style={{ fontSize: 60, marginBottom: 10 }}>📚</span>
                        <p>Your library is empty</p>
                    </div>
                ) : (
                    items.map((item, i) => (
                        <div key={i} onClick={() => onSelect(item)} style={{ padding: 15, borderBottom: '1px solid #eee', cursor: 'pointer' }}>
                            <h4 style={{ fontSize: 14, marginBottom: 5 }}>{item.person.first_name}</h4>
                            <p style={{ fontSize: 12, color: '#666' }}>{item.person.book}</p>
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}

export default function Home() {
    const [desiredAge, setDesiredAge] = useState(30)
    const [persons, setPersons] = useState([])
    const [loading, setLoading] = useState(true)
    const [currentIndex, setCurrentIndex] = useState(0)
    const [showReader, setShowReader] = useState(false)
    const [showLibrary, setShowLibrary] = useState(false)
    const [library, setLibrary] = useState([])

    useEffect(() => {
        fetchPersons()
            .then(data => {
                const shuffled = [...data].sort(() => Math.random() - 0.5)
                setPersons(shuffled)
                setLoading(false)
            })
            .catch(() => setLoading(false))
    }, [])

    const currentPerson = persons[currentIndex]

    const handleSwipe = (direction) => {
        if (direction === 'right') {
            setShowReader(true)
        } else {
            setCurrentIndex(i => (i + 1) % persons.length)
        }
    }

    const handleAddToLibrary = (person) => {
        if (!library.find(item => item.person.name === person.name)) {
            setLibrary([...library, { person, index: currentIndex }])
        }
        setShowReader(false)
        setCurrentIndex(i => (i + 1) % persons.length)
    }

    const handleCloseReader = () => {
        setShowReader(false)
        setCurrentIndex(i => (i + 1) % persons.length)
    }

    const handleLibrarySelect = (item) => {
        const idx = persons.findIndex(p => p.name === item.person.name)
        if (idx !== -1) {
            setCurrentIndex(idx)
        }
        setShowReader(true)
        setShowLibrary(false)
    }

    if (loading) {
        return (
            <div style={{ width: '100%', maxWidth: 400, height: '100vh', maxHeight: 700, background: '#fff', borderRadius: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                Loading...
            </div>
        )
    }

    if (!currentPerson) {
        return (
            <div style={{ width: '100%', maxWidth: 400, height: '100vh', maxHeight: 700, background: '#fff', borderRadius: 20, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: 60 }}>💔</span>
                <p>No more people</p>
            </div>
        )
    }

    return (
        <div style={{
            width: '100%',
            maxWidth: 400,
            height: '100vh',
            maxHeight: 700,
            background: '#fff',
            borderRadius: 20,
            boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
        }}>
            <div style={{
                padding: '15px 20px',
                background: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%)',
                color: 'white',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <h1 style={{ fontSize: 22 }}>Ancient Tinder</h1>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <label style={{ fontSize: 12 }}>Age:</label>
                    <input
                        type="number"
                        value={desiredAge}
                        onChange={(e) => setDesiredAge(parseInt(e.target.value) || 30)}
                        min="1"
                        max="100"
                        style={{ width: 60, padding: '5px 8px', border: 'none', borderRadius: 15, textAlign: 'center', fontSize: 14 }}
                    />
                </div>
            </div>

            <div style={{ flex: 1, position: 'relative', overflow: 'hidden', padding: 20 }}>
                {currentIndex + 1 < persons.length && (
                    <div style={{
                        position: 'absolute',
                        width: 'calc(100% - 40px)',
                        height: 'calc(100% - 40px)',
                        background: 'white',
                        borderRadius: 15,
                        boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                        transform: 'scale(0.95)',
                        opacity: 0.5,
                    }}>
                        <div style={{ width: '100%', height: '65%', background: 'linear-gradient(45deg, #f093fb, #f5576c)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 120, color: 'white' }}>👤</div>
                    </div>
                )}

                <Card
                    key={currentPerson.name}
                    person={currentPerson}
                    desiredAge={desiredAge}
                    onSwipe={handleSwipe}
                />
            </div>

            <div style={{ display: 'flex', justifyContent: 'center', gap: 30, padding: 20 }}>
                <button
                    onClick={() => handleSwipe('left')}
                    style={{ width: 60, height: 60, borderRadius: '50%', border: 'none', cursor: 'pointer', fontSize: 24, background: 'white', color: '#F44336', boxShadow: '0 4px 15px rgba(244, 67, 54, 0.3)' }}
                >✕</button>
                <button
                    onClick={() => setShowLibrary(true)}
                    style={{ width: 60, height: 60, borderRadius: '50%', border: 'none', cursor: 'pointer', fontSize: 24, background: 'white', color: '#2196F3', boxShadow: '0 4px 15px rgba(33, 150, 243, 0.3)' }}
                >📚</button>
                <button
                    onClick={() => handleSwipe('right')}
                    style={{ width: 60, height: 60, borderRadius: '50%', border: 'none', cursor: 'pointer', fontSize: 24, background: 'white', color: '#4CAF50', boxShadow: '0 4px 15px rgba(76, 175, 80, 0.3)' }}
                >♥</button>
            </div>

            {showReader && (
                <Reader
                    person={currentPerson}
                    personIndex={currentIndex}
                    desiredAge={desiredAge}
                    onClose={handleCloseReader}
                    onAddToLibrary={handleAddToLibrary}
                />
            )}

            <Library
                isOpen={showLibrary}
                onClose={() => setShowLibrary(false)}
                items={library}
                onSelect={handleLibrarySelect}
            />
        </div>
    )
}
