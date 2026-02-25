from fastapi import FastAPI, HTTPException, status, Response
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re

app = FastAPI(
    title="Library API",
    description="""
## Bienvenue sur l'API Library 📚

Cette API permet de gérer une bibliothèque de livres.

### Fonctionnalités :
- **Ajouter** des livres
- **Consulter** la liste des livres
- **Rechercher** par titre ou auteur
- **Trier** par année, titre ou auteur
- **Modifier** un livre
- **Supprimer** un livre
    """,
    version="1.0.0",
    contact={
        "name": "Library API",
        "email": "contact@library.com"
    }
)

class Book(BaseModel):
    id: Optional[int] = Field(None, description="ID unique (auto-généré)")
    title: str = Field(..., min_length=3, max_length=200, description="Titre du livre")
    author: str = Field(..., min_length=2, max_length=100, description="Auteur du livre")
    year: Optional[int] = Field(None, ge=1000, le=2100, description="Année de publication")
    genre: Optional[str] = Field(None, max_length=50, description="Genre littéraire")
    isbn: Optional[str] = Field(None, max_length=17, description="Code ISBN-13")

    @field_validator("isbn")
    def valider_isbn(cls, v):
        if v is None:
            return v
        pattern = r"^97[89]-\d{10}$"
        if not re.match(pattern, v):
            raise ValueError("ISBN invalide. Format attendu : 978-XXXXXXXXXX")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "genre": "Science-fiction dystopique",
                "isbn": "978-0451524935"
            }
        }
    }

books_db: List[dict] = []
next_id = 1

@app.get("/", tags=["Root"],
    summary="Page d'accueil",
    description="Retourne un message de bienvenue et les endpoints disponibles."
)
def read_root():
    return {
        "message": "Bienvenue sur l'API Library",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "books": "/books"
        }
    }

@app.get("/books", tags=["Books"],
    summary="Liste tous les livres",
    description="""
Retourne la liste des livres avec plusieurs options :
- **author** : filtrer par auteur
- **search** : rechercher un mot dans le titre
- **sort** : trier par title, author ou year
- **order** : asc (croissant) ou desc (décroissant)
- **page** : numéro de la page
- **limit** : nombre de livres par page
    """
)
def get_books(
    author: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    order: Optional[str] = "asc",
    page: int = 1,
    limit: int = 10
):
    result = books_db.copy()

    # 1. Filtrage par auteur
    if author:
        result = [b for b in result if author.lower() in b["author"].lower()]

    # 2. Recherche dans les titres
    if search:
        result = [b for b in result if search.lower() in b["title"].lower()]

    # 3. Tri
    if sort and sort in ["title", "author", "year"]:
        reverse = (order == "desc")
        result = sorted(result, key=lambda b: b.get(sort) or "", reverse=reverse)

    # 4. Pagination
    total = len(result)
    start = (page - 1) * limit
    end = start + limit
    result = result[start:end]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "books": result
    }

@app.get("/books/{book_id}", tags=["Books"],
    summary="Trouver un livre",
    description="Retourne un seul livre grâce à son ID."
)
def get_book(book_id: int):
    for book in books_db:
        if book["id"] == book_id:
            return book
    raise HTTPException(
        status_code=404,
        detail=f"Livre avec l'ID {book_id} non trouvé"
    )

@app.post("/books", status_code=201, tags=["Books"],
    summary="Ajouter un livre",
    description="Ajoute un nouveau livre dans la bibliothèque."
)
def create_book(book: Book, response: Response):
    global next_id
    new_book = book.model_dump()
    new_book["id"] = next_id
    response.headers["Location"] = f"/books/{next_id}"
    next_id += 1
    books_db.append(new_book)
    return new_book

@app.put("/books/{book_id}", tags=["Books"],
    summary="Modifier un livre entièrement",
    description="Remplace toutes les informations d'un livre existant."
)
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

@app.patch("/books/{book_id}", tags=["Books"],
    summary="Modifier partiellement un livre",
    description="Modifie seulement certaines informations d'un livre."
)
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

@app.delete("/books/{book_id}", tags=["Books"],
    summary="Supprimer un livre",
    description="Supprime définitivement un livre de la bibliothèque."
)
def delete_book(book_id: int):
    for i, book in enumerate(books_db):
        if book["id"] == book_id:
            books_db.pop(i)
            return {"message": f"Livre {book_id} supprimé avec succès"}
    raise HTTPException(
        status_code=404,
        detail=f"Livre avec l'ID {book_id} non trouvé"
    )