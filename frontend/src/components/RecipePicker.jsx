import { UtensilsCrossed, ChefHat, X } from 'lucide-react';

/**
 * RecipePicker — Glassmorphic popup overlay that appears when
 * Gemini finds recipes from Spoonacular. Shows up to 3 recipe cards
 * for the user to choose from.
 */
export function RecipePicker({ recipes, onSelect, onClose }) {
  if (!recipes || recipes.length === 0) return null;

  // Only show first 3 recipes
  const displayRecipes = recipes.slice(0, 3);

  return (
    <div className="recipe-picker-overlay">
      <div className="recipe-picker-panel glass-panel animate-in">
        <div className="recipe-picker-header">
          <div className="flex items-center gap-2">
            <ChefHat size={20} className="text-accent-color" />
            <h2 className="text-lg font-semibold tracking-tight">Pick a Recipe</h2>
          </div>
          <p className="text-sm text-slate-400 mt-1">Tell me which one you'd like to cook!</p>
        </div>

        <div className="recipe-picker-cards">
          {displayRecipes.map((recipe, index) => (
            <div 
              key={recipe.id}
              className="recipe-card"
              onClick={() => onSelect(recipe)}
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {/* Recipe Image */}
              {recipe.image && (
                <div className="recipe-card-image">
                  <img src={recipe.image} alt={recipe.name} />
                </div>
              )}

              {/* Recipe Info */}
              <div className="recipe-card-info">
                <h3 className="recipe-card-name">{recipe.name}</h3>
                
                <div className="recipe-card-meta">
                  <span className="recipe-match">
                    {recipe.match_percentage}% match
                  </span>
                  <span className="recipe-steps-count">
                    <UtensilsCrossed size={12} />
                    {recipe.steps?.length || 0} steps
                  </span>
                </div>

                {recipe.missing_ingredients?.length > 0 && (
                  <div className="recipe-card-missing">
                    <span className="text-xs text-slate-500">Missing: </span>
                    <span className="text-xs text-slate-400">
                      {recipe.missing_ingredients.slice(0, 3).join(', ')}
                      {recipe.missing_ingredients.length > 3 && ` +${recipe.missing_ingredients.length - 3} more`}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
