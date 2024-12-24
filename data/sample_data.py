from datetime import datetime

SAMPLE_RECIPES = [
    {
        "title": "Tortilla de Patatas de la yaya Alba",
        "description": "La clásica tortilla con patatas pochadas y cebolla dulce, el plato estrella de la abuela que siempre nos hace felices",
        "text": """# Tortilla de Patatas de la yaya Alba

## Ingredientes
- 4 patatas medianas (de las que te gustan a ti, mi vida, las que no son muy viejas)
- 1 cebolla grande (yo uso la blanca, que es más dulce)
- 4 huevos (tienen que ser frescos)
- Aceite de oliva virgen extra (el bueno, que para la tortilla no se escatima)
- Un pellizquito de sal (al gusto, pero con cariño)

## Preparación
1. Primero, pela las patatas con cuidadito y córtalas en rodajas finitas, como siempre te enseñé
2. La cebolla la picas en juliana, pero no muy fina que si no se quema
3. Pon abundante aceite en la sartén (sí, sí, no seas rata con el aceite que es importante)
4. Fríe las patatas y la cebolla a fuego suavecito, que se tienen que hacer despacito. Esto es lo más importante, tesoro
5. Cuando veas que las patatas están blanditas y la cebolla transparente (tú ya sabes, como las que hacíamos juntos), las sacas y escurres el aceite
6. Bate los huevos en un bol grande (dales bien, que queden espumositos)
7. Mezcla las patatas y la cebolla con los huevos, con mucho cuidado para no romper las patatas
8. Déjalo reposar 5 minutitos, que se conozcan los sabores
9. Ahora viene el arte: cuaja la tortilla a fuego medio, dale la vuelta con un plato (como te enseñé mil veces)

## Notas
- El secreto está en el cariño y en dejar las patatas bien pochadas, que se deshagan en la boca
- No tengas prisa, que las prisas no son buenas para la cocina
- Si la quieres jugosita por dentro, no la dejes mucho tiempo. A tu abuelo le gusta más cuajada, pero yo siempre la hago jugosa
- La cebolla es opcional, pero para mí es el secreto del sabor. Como dice mi madre: "tortilla sin cebolla es como un jardín sin flores"
- Si sobra (que nunca sobra), está buenísima al día siguiente entre pan""",
        "created_at": datetime(2024, 3, 15, 12, 0, 0),
        "slug": "tortilla-patatas-20240315"
    },
    {
        "title": "Arroz con Leche de la yaya María",
        "description": "El postre más cremoso y reconfortante, con el toque especial del limón y la canela que solo la yaya sabe darle",
        "text": """# Arroz con Leche de la yaya María

## Ingredientes
- 1 vasito de arroz (el mismo que uso para el café, más o menos 100g)
- 1 litro de leche entera (tiene que ser entera, mi vida, si no, no sale igual)
- 1 palito de canela
- La piel de un limón (pero solo la parte amarillita)
- 2 puñaditos de azúcar (luego pruebas y añades más si hace falta)
- Un pellizquito de sal
- Canela en polvo para decorar

## Preparación
1. Primero lava bien el arroz con agua fresquita, hasta que salga clarita
2. Pon la leche en un cazo a fuego suave con la canela en rama y la piel de limón
3. Cuando empiece a humear (pero sin que llegue a hervir), echa el arroz y el pellizquito de sal
4. Ahora viene lo importante, mi amor: hay que remover con mucho cariño y paciencia, siempre en el mismo sentido para que salga cremosito
5. Déjalo a fuego suavecito unos 45 minutitos, removiendo de vez en cuando para que no se pegue
6. Cuando el arroz esté tierno, añade el azúcar y remueve otros 5 minutitos
7. Retira la canela y la piel de limón, y deja que repose un poquito

## Notas
- El secreto está en remover con mucho amor y paciencia
- Si ves que queda muy espeso, puedes añadir un chorrito de leche caliente
- A mis nietos les encanta tomarlo templado con un poquito de canela por encima
- Si sobra (que lo dudo, cariño), en la nevera dura 2-3 días""",
        "created_at": datetime(2024, 3, 16, 15, 30, 0),
        "slug": "arroz-con-leche-20240316"
    },
    {
        "title": "Crepes Favoritos de Marco",
        "description": "La receta perfecta de crepes, con la masa suave y sin grumos, ideal para rellenar al gusto",
        "text": """# Crepes Favoritos de Marco

## Ingredientes
- 400 gramos de harina
- medio litro de leche
- 4 huevos
- una pizquina de sal
- 50 gramos de mantequilla derretida

## Preparación
1. En un bol, poner la harina, la leche, los huevos, la pizquina de sal y la mantequilla derretida.
2. Mover bien la mezcla hasta que esté todo bien movido y sin grumos. Tiene que tener la consistencia de nata líquida, un poquito más espeso.
3. Dejar reposar la mezcla durante 30 minutos.
4. Calentar una sartén y poner un poquito de mantequilla.
5. Cuando esté un poco calientita, echar una cucharada de masa en la sartén.
6. Cuando veas que se ha hecho un poco, girar la crepe y acabar de cocinarla.
7. Rellenar al gusto.

## Notas
- Esta receta puede hacerse con la Thermomix, pero también es fácil sin ella.
- Recuerda que la clave está en que esté bien movido y sin grumos. ¡Espero que os guste!""",
        "created_at": datetime(2024, 3, 17, 10, 0, 0),
        "slug": "crepes-marco-20240317"
    }
]

def get_sample_recipes():
    return SAMPLE_RECIPES