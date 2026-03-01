from fastapi import FastAPI, HTTPException, status, Response, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from auth import creer_token, verifier_token, verifier_mot_de_passe, users_db
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

### Codes de réponse :
- **200** : Succès
- **201** : Livre créé avec succès
- **401** : Non autorisé
- **404** : Livre non trouvé
- **422** : Données invalides
    """,
    version="1.0.0",
    contact={
        "name": "Library API",
        "email": "contact@library.com"
    }
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    username = verifier_token(token)
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Token invalide ou expiré"
        )
    return username

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int]
    genre: Optional[str]
    isbn: Optional[str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "genre": "Science-fiction dystopique",
                "isbn": "978-0451524935"
            }
        }
    }

class BooksListResponse(BaseModel):
    total: int
    page: int
    limit: int
    books: List[BookResponse]

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
    description="Retourne un message de bienvenue."
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

@app.post("/login", tags=["Auth"],
    summary="Se connecter",
    description="Envoie ton login et mot de passe, reçois un token JWT."
)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or not verifier_mot_de_passe(form_data.password, user["password"]):
        raise HTTPException(
            status_code=401,
            detail="Login ou mot de passe incorrect"
        )
    token = creer_token({"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/books", tags=["Books"],
    summary="Liste tous les livres",
    response_model=BooksListResponse,
    responses={
        200: {"description": "Liste des livres retournée avec succès"},
        422: {"description": "Paramètres invalides"}
    },
    description="""
Retourne la liste des livres avec plusieurs options :
- **author** : filtrer par auteur (ex: Orwell)
- **search** : rechercher un mot dans le titre (ex: prince)
- **sort** : trier par `title`, `author` ou `year`
- **order** : `asc` (croissant) ou `desc` (décroissant)
- **page** : numéro de la page (défaut: 1)
- **limit** : nombre de livres par page (défaut: 10)
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

    if author:
        result = [b for b in result if author.lower() in b["author"].lower()]

    if search:
        result = [b for b in result if search.lower() in b["title"].lower()]

    if sort and sort in ["title", "author", "year"]:
        reverse = (order == "desc")
        result = sorted(result, key=lambda b: b.get(sort) or "", reverse=reverse)

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
    response_model=BookResponse,
    responses={
        200: {"description": "Livre trouvé avec succès"},
        404: {"description": "Livre non trouvé"}
    },
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
    response_model=BookResponse,
    responses={
        201: {"description": "Livre créé avec succès"},
        401: {"description": "Non autorisé"},
        422: {"description": "Données invalides"}
    },
    description="Ajoute un nouveau livre. Nécessite un token JWT."
)
def create_book(book: Book, response: Response, current_user: str = Depends(get_current_user)):
    global next_id
    new_book = book.model_dump()
    new_book["id"] = next_id
    response.headers["Location"] = f"/books/{next_id}"
    next_id += 1
    books_db.append(new_book)
    return new_book

@app.put("/books/{book_id}", tags=["Books"],
    summary="Modifier un livre entièrement",
    response_model=BookResponse,
    responses={
        200: {"description": "Livre modifié avec succès"},
        401: {"description": "Non autorisé"},
        404: {"description": "Livre non trouvé"}
    },
    description="Remplace toutes les informations d'un livre. Nécessite un token JWT."
)
def update_book(book_id: int, book: Book, current_user: str = Depends(get_current_user)):
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
    response_model=BookResponse,
    responses={
        200: {"description": "Livre modifié avec succès"},
        401: {"description": "Non autorisé"},
        404: {"description": "Livre non trouvé"}
    },
    description="Modifie seulement certaines informations d'un livre. Nécessite un token JWT."
)
def partial_update_book(book_id: int, book: Book, current_user: str = Depends(get_current_user)):
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
    responses={
        200: {"description": "Livre supprimé avec succès"},
        401: {"description": "Non autorisé"},
        404: {"description": "Livre non trouvé"}
    },
    description="Supprime définitivement un livre. Nécessite un token JWT."
)
def delete_book(book_id: int, current_user: str = Depends(get_current_user)):
    for i, book in enumerate(books_db):
        if book["id"] == book_id:
            books_db.pop(i)
            return {"message": f"Livre {book_id} supprimé avec succès"}
    raise HTTPException(
        status_code=404,
        detail=f"Livre avec l'ID {book_id} non trouvé"
    )