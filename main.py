from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(
    title="Library API",
    description="API REST pour gérer une bibliothèque de livres",
    version="1.0.0"
)

class Book(BaseModel):
    id: Optional[int] = Field(None, description="ID unique (auto-généré)")
    title: str = Field(..., min_length=3, max_length=200, description="Titre du livre")
    author: str = Field(..., min_length=2, max_length=100, description="Auteur du livre")
    year: Optional[int] = Field(None, ge=1000, le=2100, description="Année de publication")
    genre: Optional[str] = Field(None, max_length=50, description="Genre littéraire")
    isbn: Optional[str] = Field(None, max_length=17, description="Code ISBN-13")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "genre": "Science-fiction dystopique",
                "isbn": "978-0451524935"
            }
        }

books_db: List[dict] = []
next_id = 1

@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Bienvenue sur l'API Library",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "books": "/books"
        }
    }

@app.get("/books", tags=["Books"])
def get_books():
    return books_db

@app.get("/books/{book_id}", tags=["Books"])
def get_book(book_id: int):
    for book in books_db:
        if book["id"] == book_id:
            return book
    raise HTTPException(
        status_code=404,
        detail=f"Livre avec l'ID {book_id} non trouvé"
    )

@app.post("/books", status_code=201, tags=["Books"])
def create_book(book: Book):
    global next_id
    new_book = book.model_dump()
    new_book["id"] = next_id
    next_id += 1
    books_db.append(new_book)
    return new_book

@app.put("/books/{book_id}", tags=["Books"])
def update_book(book_id: int, book: Book):
    for i, existing_book in enumerate(books_db):
        if existing_book["id"] == book_id:
            updated_book = book.model_dump()
            updated_book["id"] = book_id
            books_db[i] = updated_book
            return updated_book
    raise HTTPException(
        status_code=404,
        detail=f"Livre avec l'ID {book_id} non trouvé"
    )

@app.patch("/books/{book_id}", tags=["Books"])
def partial_update_book(book_id: int, book: Book):
    for i, existing_book in enumerate(books_db):
        if existing_book["id"] == book_id:
            update_data = book.model_dump(exclude_unset=True)
            existing_book.update(update_data)
            return existing_book
    raise HTTPException(
        status_code=404,
        detail=f"Livre avec l'ID {book_id} non trouvé"
    )

@app.delete("/books/{book_id}", tags=["Books"])
def delete_book(book_id: int):
    for i, book in enumerate(books_db):
        if book["id"] == book_id:
            books_db.pop(i)
            return {"message": f"Livre {book_id} supprimé avec succès"}
    raise HTTPException(
        status_code=404,
        detail=f"Livre avec l'ID {book_id} non trouvé"
    )