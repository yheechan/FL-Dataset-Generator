#include "../music_utility.h"
#include "olrn.h"

extern set<string> logical_operators;
extern set<string> relational_operators;

bool OLRN::ValidateDomain(const std::set<std::string> &domain)
{
	for (auto it: domain)
  	if (logical_operators.find(it) == logical_operators.end())
    	// cannot find input domain inside valid domain
      return false;

  return true;
}

bool OLRN::ValidateRange(const std::set<std::string> &range)
{
	for (auto it: range)
  	if (relational_operators.find(it) == relational_operators.end())
    	// cannot find input range inside valid range
      return false;

  return true;
}

void OLRN::setDomain(std::set<std::string> &domain)
{
	if (domain.empty())
		domain_ = logical_operators;
	else
		domain_ = domain;
}

void OLRN::setRange(std::set<std::string> &range)
{
	if (range.empty())
		range_ = relational_operators;
	else
		range_ = range;
}

bool OLRN::IsMutationTarget(clang::Expr *e, MusicContext *context)
{
	if (BinaryOperator *bo = dyn_cast<BinaryOperator>(e))
	{
		string binary_operator{bo->getOpcodeStr()};
		SourceLocation start_loc = bo->getOperatorLoc();
		SourceManager &src_mgr = context->comp_inst_->getSourceManager();

		// cout << "cp olrn\n";
		SourceLocation end_loc = src_mgr.translateLineCol(
				src_mgr.getMainFileID(),
				GetLineNumber(src_mgr, start_loc),
				GetColumnNumber(src_mgr, start_loc) + binary_operator.length());
		StmtContext &stmt_context = context->getStmtContext();

		// Return True if expr is in mutation range, NOT inside array decl size
		// and NOT inside enum declaration.
		if (context->IsRangeInMutationRange(SourceRange(start_loc, end_loc)) &&
				!stmt_context.IsInArrayDeclSize() &&
				!stmt_context.IsInEnumDecl() &&
				domain_.find(binary_operator) != domain_.end())
			return true;
	}

	return false;
}



void OLRN::Mutate(clang::Expr *e, MusicContext *context)
{
	BinaryOperator *bo;
	if (!(bo = dyn_cast<BinaryOperator>(e)))
		return;

	string token{bo->getOpcodeStr()};
	string typestring{"int"};

	CXXOperatorCallExpr *lhs_bo;
	CXXOperatorCallExpr *rhs_bo;

	BinaryOperator *lhs_bo_x;
	BinaryOperator *rhs_bo_x;


	bool modified_lhs = false;
	bool modified_rhs = false;


	SourceLocation start_loc = bo->getOperatorLoc();
	SourceManager &src_mgr = context->comp_inst_->getSourceManager();
	// cout << "cp olrn\n";
	SourceLocation end_loc = src_mgr.translateLineCol(
			src_mgr.getMainFileID(),
			GetLineNumber(src_mgr, start_loc),
			GetColumnNumber(src_mgr, start_loc) + token.length());

	Expr* lhs = bo->getLHS();
	Expr* rhs = bo->getRHS();
	// lhs->dump();
	// rhs->dump();
	string lhs_token = ConvertToString(lhs, context->comp_inst_->getLangOpts());
	string rhs_token = ConvertToString(rhs, context->comp_inst_->getLangOpts());
	// cout<<"lhs_token: "<<lhs_token<<endl;
	// cout<<"rhs_token: "<<rhs_token<<endl;

	if(lhs_bo = dyn_cast<CXXOperatorCallExpr>(lhs)){
		// cout<<"meiwenti"<<endl;
		modified_lhs = true;
		lhs_token.insert(0, "(");
		lhs_token.append(")");
		start_loc = lhs->getBeginLoc();
	} else 	if(lhs_bo_x = dyn_cast<BinaryOperator>(lhs)){
		// cout<<"meiwenti"<<endl;
		modified_lhs = true;
		lhs_token.insert(0, "(");
		lhs_token.append(")");
		start_loc = lhs->getBeginLoc();
	}

	if(rhs_bo = dyn_cast<CXXOperatorCallExpr>(rhs)){
		modified_rhs = true;
		rhs_token.insert(0, "(");
		rhs_token.append(")");
		SourceLocation r_start_loc = rhs->getBeginLoc();
		end_loc = rhs->getEndLoc();
		unsigned tokenLength = Lexer::MeasureTokenLength(end_loc, context->comp_inst_->getSourceManager(), context->comp_inst_->getLangOpts());
    	end_loc = end_loc.getLocWithOffset(tokenLength);
	} else	if(rhs_bo_x = dyn_cast<BinaryOperator>(rhs)){
		modified_rhs = true;
		rhs_token.insert(0, "(");
		rhs_token.append(")");
		SourceLocation r_start_loc = rhs->getBeginLoc();
		end_loc = rhs->getEndLoc();
		unsigned tokenLength = Lexer::MeasureTokenLength(end_loc, context->comp_inst_->getSourceManager(), context->comp_inst_->getLangOpts());
    	end_loc = end_loc.getLocWithOffset(tokenLength);
	}



	string eq{"=="};
	string ieq{"!="};
	StmtContext &stmt_context = context->getStmtContext();


	for (auto mutated_token: range_)
		if (token.compare(mutated_token) != 0)
		{

			if(stmt_context.IsEnumClassType() && (mutated_token.compare(eq) == 0 || mutated_token.compare(ieq) == 0)){

				if(modified_lhs){
					mutated_token.insert(0, lhs_token);
				}

				if(modified_rhs){
					mutated_token.append(rhs_token);
				}

				context->mutant_database_.AddMutantEntry(context->getStmtContext(),
						name_, start_loc, end_loc, token, mutated_token, 
						context->getStmtContext().getProteumStyleLineNum(), token+mutated_token);
			}
			else{

				if(modified_lhs){
					mutated_token.insert(0, lhs_token);
				}

				if(modified_rhs){
					mutated_token.append(rhs_token);
				}
				context->mutant_database_.AddMutantEntry(context->getStmtContext(),
						name_, start_loc, end_loc, token, mutated_token, 
						context->getStmtContext().getProteumStyleLineNum(), token+mutated_token);
			}
		}
}

