#include "../music_utility.h"
#include "vdtr.h"

bool VDTR::ValidateDomain(const std::set<std::string> &domain)
{
  for (auto e: domain)
    if (!IsValidVariableName(e))
      return false;

  return true;

  // return domain.empty();
}

bool VDTR::ValidateRange(const std::set<std::string> &range)
{
  // for (auto e: range)
  //   if (!IsValidVariableName(e))
  //     return false;

  return true;

  // return range.empty();
}

// Return True if the mutant operator can mutate this expression
bool VDTR::IsMutationTarget(clang::Expr *e, MusicContext *context)
{
  if (!ExprIsScalarReference(e))
    return false;

  SourceLocation start_loc = e->getBeginLoc();
  SourceLocation end_loc = GetEndLocOfExpr(e, context->comp_inst_);
  StmtContext &stmt_context = context->getStmtContext();

  for(auto l_value_arg: (*(context->getSymbolTable()->getLValueArgList()))){
		SourceLocation start_loc_l = l_value_arg->getBeginLoc();
		SourceLocation end_loc_l = GetEndLocOfExpr(l_value_arg, context->comp_inst_);
		if(start_loc_l == start_loc && end_loc_l == end_loc){
			// cout<<"wozhengdemeiyouwenti"<<endl;
			// cout<<"expr: "<<ConvertToString(e, context->comp_inst_->getLangOpts())<<endl;
			return false;
		}
	}

  SourceManager &src_mgr = context->comp_inst_->getSourceManager();
  string token{ConvertToString(e, context->comp_inst_->getLangOpts())};
  bool is_in_domain = domain_.empty() ? true : 
                      IsStringElementOfSet(token, domain_);
  

  return context->IsRangeInMutationRange(SourceRange(start_loc, end_loc)) &&
         !stmt_context.IsInEnumDecl() &&
        //  !stmt_context.IsEnumClassType() &&
         !stmt_context.IsInArrayDeclSize() &&
         !stmt_context.IsInLhsOfAssignmentRange(e) &&
         !stmt_context.IsInUnaryIncrementDecrementRange(e) &&
         !stmt_context.IsInAddressOpRange(e) &&
         !stmt_context.IsInSwitchCaseRange(e)&&
         stmt_context.IsInCurrentlyParsedFunctionRange(e) &&
         is_in_domain;
}

void VDTR::Mutate(clang::Expr *e, MusicContext *context)
{
  SourceLocation start_loc = e->getBeginLoc();
  SourceLocation end_loc = GetEndLocOfExpr(e, context->comp_inst_);
  SourceManager &src_mgr = context->comp_inst_->getSourceManager();

  string token{ConvertToString(e, context->comp_inst_->getLangOpts())};

  SourceLocation start_of_file = src_mgr.getLocForStartOfFile(src_mgr.getMainFileID());
  vector<string> extra_tokens{""};
  vector<string> extra_mutated_tokens{"#include <sys/types.h>\n#include <signal.h>\n#include <unistd.h>\n"};
  vector<SourceLocation> extra_start_locs{start_of_file};
  vector<SourceLocation> extra_end_locs{start_of_file};
  StmtContext &stmt_context = context->getStmtContext();

  string mutated_token_neg{"((" + token + ") < 0 ? kill(getpid(), 9) : (" + token + "))"};
  string mutated_token_zero{"((" + token + ") == 0 ? kill(getpid(), 9) : (" + token + "))"};
  string mutated_token_pos{"((" + token + ") > 0 ? kill(getpid(), 9) : (" + token + "))"};
  auto Canonicaltype = (e->getType()).getCanonicalType();
  if(const auto *BT = dyn_cast<BuiltinType>(Canonicaltype) ){
    if(BT->getKind() != BuiltinType::Int){
      string type_ = e->getType().getDesugaredType(context->comp_inst_->getASTContext()).getAsString();
      _BoolTobool(type_);
      mutated_token_neg = "((" + token + ") < 0 ? static_cast<" + type_ + ">(kill(getpid(), 9)) : (" + token + "))";
      mutated_token_zero = "((" + token + ") == 0 ? static_cast<" + type_ + ">(kill(getpid(), 9)) : (" + token + "))";
      mutated_token_pos = "((" + token + ") > 0 ? static_cast<" + type_ + ">(kill(getpid(), 9)) : (" + token + "))";  
    }
  }
  if(ExprIsEnum(e)||ExprIsEnumClass(e)){
    string type_ = e->getType().getDesugaredType(context->comp_inst_->getASTContext()).getAsString();
    _BoolTobool(type_);
    mutated_token_neg = "((" + token + ") < 0 ? static_cast<" + type_ + ">(kill(getpid(), 9)) : (" + token + "))";
    mutated_token_zero = "((" + token + ") == 0 ? static_cast<" + type_ + ">(kill(getpid(), 9)) : (" + token + "))";
    mutated_token_pos = "((" + token + ") < 0 ? static_cast<" + type_ + ">(kill(getpid(), 9)) : (" + token + "))";
  }
    if(ExprIsEnumClass(e)){
    mutated_token_neg.insert(1, " static_cast<int>");
    mutated_token_zero.insert(1, " static_cast<int>");
    mutated_token_pos.insert(1, " static_cast<int>");
  }

  context->mutant_database_.AddMutantEntry(context->getStmtContext(),
      name_, start_loc, end_loc, token, mutated_token_neg, 
      context->getStmtContext().getProteumStyleLineNum(), "NEG",
      extra_tokens, extra_mutated_tokens, extra_start_locs, extra_end_locs);

  context->mutant_database_.AddMutantEntry(context->getStmtContext(),
      name_, start_loc, end_loc, token, mutated_token_zero, 
      context->getStmtContext().getProteumStyleLineNum(), "ZERO",
      extra_tokens, extra_mutated_tokens, extra_start_locs, extra_end_locs);

  context->mutant_database_.AddMutantEntry(context->getStmtContext(),
      name_, start_loc, end_loc, token, mutated_token_pos, 
      context->getStmtContext().getProteumStyleLineNum(), "POS",
      extra_tokens, extra_mutated_tokens, extra_start_locs, extra_end_locs);
}
