import { ChefHat, Clock, ShoppingCart } from 'lucide-react';

/**
 * Returns a relevant food emoji based on recipe name keywords.
 * Used as the card "image" since external image APIs are unreliable.
 */
function getRecipeEmoji(name = '') {
  const n = name.toLowerCase();
  if (n.includes('chicken')) return '🍗';
  if (n.includes('pasta') || n.includes('spaghetti') || n.includes('bolognese') || n.includes('carbonara') || n.includes('linguine') || n.includes('penne')) return '🍝';
  if (n.includes('fried rice') || n.includes('rice')) return '🍚';
  if (n.includes('egg') || n.includes('omelette') || n.includes('scramble') || n.includes('frittata')) return '🍳';
  if (n.includes('salad')) return '🥗';
  if (n.includes('soup') || n.includes('stew') || n.includes('curry') || n.includes('chili')) return '🍲';
  if (n.includes('cake') || n.includes('cookie') || n.includes('brownie') || n.includes('muffin')) return '🍰';
  if (n.includes('pizza')) return '🍕';
  if (n.includes('burger')) return '🍔';
  if (n.includes('fish') || n.includes('salmon') || n.includes('tuna') || n.includes('cod')) return '🐟';
  if (n.includes('oat') || n.includes('porridge') || n.includes('granola') || n.includes('cereal')) return '🥣';
  if (n.includes('sandwich') || n.includes('toast') || n.includes('wrap')) return '🥪';
  if (n.includes('steak') || n.includes('beef') || n.includes('mince') || n.includes('ground beef')) return '🥩';
  if (n.includes('shrimp') || n.includes('prawn') || n.includes('seafood')) return '🦐';
  if (n.includes('taco') || n.includes('burrito') || n.includes('quesadilla')) return '🌮';
  if (n.includes('pancake') || n.includes('waffle')) return '🥞';
  if (n.includes('smoothie') || n.includes('juice')) return '🥤';
  if (n.includes('avocado')) return '🥑';
  if (n.includes('mushroom')) return '🍄';
  return '🍴';
}

/**
 * RecipePicker — Glassmorphic popup overlay that appears when
 * Gemini finds recipes from ingredients. Shows up to 3 recipe cards.
 */
export function RecipePicker({ recipes, onSelect, onClose }) {
  if (!recipes || recipes.length === 0) return null;

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
              {/* Emoji Image — always works, no external URL needed */}
              <div
                className="recipe-card-image"
                style={{
                  background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '2.5rem', // Slightly smaller default
                  userSelect: 'none',
                }}
              >
                {getRecipeEmoji(recipe.name)}
              </div>

              {/* Recipe Info */}
              <div className="recipe-card-info">
                <h3 className="recipe-card-name">{recipe.name}</h3>

                <div className="recipe-card-meta">
                  {/* Estimated time */}
                  {recipe.estimated_time && (
                    <span className="recipe-match flex items-center gap-1">
                      <Clock size={11} />
                      {recipe.estimated_time}
                    </span>
                  )}
                  {/* Extra ingredients needed */}
                  <span className="recipe-steps-count flex items-center gap-1">
                    <ShoppingCart size={11} />
                    {recipe.needs_count > 0
                      ? `needs ${recipe.needs_count} more`
                      : 'no extras needed'}
                  </span>
                  {/* Step count */}
                  <span className="recipe-steps-count">
                    {recipe.steps?.length || 0} steps
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
